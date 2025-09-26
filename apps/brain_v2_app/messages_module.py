import os, json, asyncio, time, datetime as dt, logging
from contextlib import asynccontextmanager
from typing import Optional, Iterable, List, Tuple

import discord
from discord import (
    TextChannel, Thread, VoiceChannel, ForumChannel, CategoryChannel, StageChannel
)
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from dotenv import load_dotenv

# --------------------------
# Config & Globals
# --------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

TOKEN    = os.getenv("DISCORD_WEBHOOK_BOT_KEY")
PG_DSN   = os.getenv("DATABASE_URL")
ORG_ID   = os.getenv("ORG_ID", "AI@DSCubed")
GUILD_ID = os.getenv("AI_AT_DSCUBED_GUILD_ID")  # single guild expected (can extend to list if needed)

# Backfill toggles
BACKFILL        = (os.getenv("DISCORD_BACKFILL", "false").lower() == "true")
BACKFILL_LIMIT  = int(os.getenv("DISCORD_BACKFILL_LIMIT", "0") or 0)  # messages per component; 0 = unlimited

# Guard envs early
for _k in ("DISCORD_WEBHOOK_BOT_KEY", "DATABASE_URL", "AI_AT_DSCUBED_GUILD_ID"):
    if not os.getenv(_k):
        raise RuntimeError(f"Missing env var: {_k}")

# Discord intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True           # needed for ACL resolution
intents.messages = True
intents.message_content = True   # needed to read content, mentions, @here detection

bot = discord.Client(intents=intents)
apool: Optional[AsyncConnectionPool] = None
_role_debounce = 0.0  # debounce for role updates

CHANNEL_TYPES = (TextChannel, Thread, VoiceChannel, ForumChannel, CategoryChannel, StageChannel)

# --------------------------
# Utilities
# --------------------------

def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def jsonb(obj) -> Optional[dict]:
    """Convert discord objects to a minimally serializable dict"""
    try:
        return json.loads(json.dumps(obj, default=lambda x: getattr(x, "id", str(x))))
    except Exception:
        return None

def get_member_id_from_row(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get("member_id")
    try:
        return row[0]
    except Exception:
        return None

async def get_linked_member_id(cur, external_id: str):
    await cur.execute("""
        select member_id
        from catalog.member_identities
        where system='discord' and external_id=%s
        limit 1
    """, (external_id,))
    return get_member_id_from_row(await cur.fetchone())

@asynccontextmanager
async def tx(aconn):
    """Explicit transaction scope; connection auto-rolls back on exception."""
    try:
        async with aconn.transaction():
            yield
    except Exception:
        raise

def classify_component(obj) -> Tuple[str, Optional[str]]:
    """
    Returns (component_type, parent_component_id)
    Types: 'guild_text','thread','forum','forum_post','voice','category','stage'
    """
    if isinstance(obj, ForumChannel):
        return ("forum", None)
    if isinstance(obj, Thread):
        parent = obj.parent.id if obj.parent else None
        if isinstance(obj.parent, ForumChannel):
            return ("forum_post", str(parent))
        return ("thread", str(parent) if parent else None)
    if isinstance(obj, TextChannel):
        return ("guild_text", str(obj.category_id) if obj.category_id else None)
    if isinstance(obj, VoiceChannel):
        return ("voice", str(obj.category_id) if obj.category_id else None)
    if isinstance(obj, StageChannel):
        return ("stage", str(obj.category_id) if obj.category_id else None)
    if isinstance(obj, CategoryChannel):
        return ("category", None)
    return (type(obj).__name__.lower(), None)

async def upsert_component_row(cur, obj, name_hint=None, raw=None):
    ctype, parent_id = classify_component(obj)
    name = getattr(obj, "name", name_hint or str(obj.id))
    await cur.execute("""
      insert into silver.components
        (org_id, system, component_id, component_type, name, parent_component_id, created_at_ts, updated_at_ts, raw)
      values
        (%s,'discord',%s,%s,%s,%s, now(), now(), %s)
      on conflict (org_id, system, component_id) do update set
        component_type=excluded.component_type,
        name=excluded.name,
        parent_component_id=excluded.parent_component_id,
        updated_at_ts=excluded.updated_at_ts,
        raw=excluded.raw
    """, (ORG_ID, str(obj.id), ctype, name, str(parent_id) if parent_id else None, json.dumps(raw) if raw else None))

# --------------------------
# Mentions
# --------------------------

async def upsert_message_mentions(aconn, msg: discord.Message):
    """
    Populate silver.message_mentions using a unique index with NULLS NOT DISTINCT
    on (message_id, mention_type, mentioned_external_id).
    """
    rows = []
    for u in msg.mentions:
        rows.append(("user", str(u.id)))
    for r in getattr(msg, "role_mentions", []):
        rows.append(("role", str(r.id)))
    for ch in getattr(msg, "channel_mentions", []):
        rows.append(("channel", str(ch.id)))
    if getattr(msg, "mention_everyone", False):
        rows.append(("everyone", None))
        if "@here" in (msg.content or ""):
            rows.append(("here", None))

    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            # idempotent: wipe then insert
            await cur.execute("delete from silver.message_mentions where message_id=%s", (str(msg.id),))
            if not rows:
                return

            values = []
            for mtype, ext in rows:
                member_uuid = None
                if mtype == "user" and ext:
                    await cur.execute("""
                      select mi.member_id
                      from catalog.member_identities mi
                      where mi.system='discord' and mi.external_id=%s
                      limit 1
                    """, (ext,))
                    r = await cur.fetchone()
                    member_uuid = get_member_id_from_row(r)
                values.append((str(msg.id), mtype, ext, member_uuid))

            await cur.executemany("""
              insert into silver.message_mentions (message_id, mention_type, mentioned_external_id, member_id)
              values (%s,%s,%s,%s)
              on conflict (message_id, mention_type, mentioned_external_id) do update
                set member_id = excluded.member_id,
                    updated_at_ts = now()
            """, values)

# --------------------------
# ACL (latest only)
# --------------------------

async def current_viewers(guild: discord.Guild, channel) -> List[discord.Member]:
    viewers = []
    for m in guild.members:
        try:
            if channel.permissions_for(m).view_channel:
                viewers.append(m)
        except Exception:
            pass
    return viewers

async def resolve_member_uuid(cur, discord_user_id: str):
    await cur.execute("""
      select member_id
      from catalog.member_identities
      where system='discord' and external_id=%s
      limit 1
    """, (discord_user_id,))
    row = await cur.fetchone()
    return get_member_id_from_row(row)

async def sync_component_access_latest(aconn, guild: discord.Guild, channel):
    """Upsert current viewers to silver.component_members; remove stale rows."""
    if isinstance(channel, CategoryChannel):
        return

    async with aconn.cursor(row_factory=dict_row) as cur:
        viewers = await current_viewers(guild, channel)
        current = {str(m.id): m for m in viewers}

        # ensure identities exist / refresh username
        for m in viewers:
            await cur.execute(
                "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                (ORG_ID, str(m.id), m.name),
            )

        # Load existing external_ids for this component
        await cur.execute("""
          select external_id
          from silver.component_members
          where system='discord' and component_id=%s
        """, (str(channel.id),))
        existing = { (row["external_id"] if isinstance(row, dict) else row[0])
                     for row in await cur.fetchall() }

        # Upserts
        upserts = []
        for ext_id, member in current.items():
            member_uuid = await resolve_member_uuid(cur, ext_id)
            upserts.append(('discord', str(channel.id), ext_id, member_uuid, True, ORG_ID))

        if upserts:
            await cur.executemany("""
              insert into silver.component_members (system, component_id, external_id, member_id, can_view, org_id, updated_at_ts)
              values (%s,%s,%s,%s,%s,%s, now())
              on conflict (org_id, system, component_id, external_id) do update
                set member_id     = excluded.member_id,
                    can_view      = excluded.can_view,
                    org_id        = excluded.org_id,
                    updated_at_ts = now()
            """, upserts)

        # Deletes
        stale_ext_ids = existing - set(current.keys())
        if stale_ext_ids:
            await cur.executemany("""
              delete from silver.component_members
              where system='discord' and component_id=%s and external_id=%s
            """, [(str(channel.id), ext) for ext in stale_ext_ids])

# --------------------------
# Forum backfill helpers
# --------------------------

async def list_forum_threads(forum: ForumChannel) -> List[Thread]:
    threads: List[Thread] = list(forum.threads)  # active
    before = None
    while True:
        fetched = 0
        async for t in forum.archived_threads(limit=100, before=before):
            threads.append(t)
            before = t
            fetched += 1
        if fetched == 0:
            break
    return threads

async def enumerate_components(guild: discord.Guild):
    """Yield each component you want to ingest exactly once."""
    for ch in guild.channels:
        if isinstance(ch, ForumChannel):
            yield ch  # forum container
            for t in await list_forum_threads(ch):
                yield t  # each forum post (Thread)
        elif isinstance(ch, TextChannel):
            yield ch
        elif isinstance(ch, Thread):
            yield ch

# --------------------------
# Backfill — single pass per component
# --------------------------

async def backfill_component(aconn, guild: discord.Guild, comp):
    """Upsert component, sync ACL, then messages→mentions→reactions (one pass)."""
    # Component upsert
    async with aconn.cursor(row_factory=dict_row) as cur:
        await upsert_component_row(cur, comp)
    await aconn.commit()

    # ACL
    await sync_component_access_latest(aconn, guild, comp)
    await aconn.commit()

    # Messages + mentions + reactions (only for TextChannel/Thread)
    if isinstance(comp, (TextChannel, Thread)):
        count = 0
        async for msg in comp.history(limit=None, oldest_first=True):
            async with aconn.cursor(row_factory=dict_row) as cur:
                # identity (no auto-member)
                await cur.execute(
                    "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                    (ORG_ID, str(msg.author.id), msg.author.name),
                )
                author_member_id = await get_linked_member_id(cur, str(msg.author.id))

                # upsert message
                await cur.execute("""
                  insert into silver.messages (
                    org_id, system, message_id, component_id, author_external_id, author_member_id,
                    content, has_attachments, reply_to_message_id, created_at_ts, raw
                  )
                  values (%s,'discord',%s,%s,%s,%s,%s,%s,%s,%s,%s)
                  on conflict (message_id) do update set
                    content=excluded.content,
                    has_attachments=excluded.has_attachments,
                    reply_to_message_id=excluded.reply_to_message_id,
                    raw=excluded.raw
                """, (
                    ORG_ID, str(msg.id), str(msg.channel.id), str(msg.author.id), author_member_id,
                    msg.content, bool(msg.attachments),
                    str(msg.reference.message_id) if (msg.reference and msg.reference.message_id) else None,
                    msg.created_at,
                    json.dumps({
                        "id": str(msg.id),
                        "channel_id": str(msg.channel.id),
                        "author_id": str(msg.author.id),
                        "created_at": msg.created_at.isoformat(),
                    }),
                ))
            # mentions (commits inside)
            await upsert_message_mentions(aconn, msg)

            # reactions (inline; at-least-once safe)
            if msg.reactions:
                async with aconn.cursor(row_factory=dict_row) as cur:
                    for reaction in msg.reactions:
                        async for user in reaction.users():
                            if user.bot:
                                continue
                            await cur.execute(
                                "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                                (ORG_ID, str(user.id), user.name),
                            )
                            member_id = await get_linked_member_id(cur, str(user.id))
                            await cur.execute("""
                                insert into silver.message_reactions (org_id, system, message_id, reaction, member_id, created_at_ts)
                                values (%s, 'discord', %s, %s, %s, %s)
                                on conflict (message_id, reaction, member_id) do nothing
                            """, (ORG_ID, str(msg.id), str(reaction.emoji), member_id, msg.created_at))
            count += 1
            if BACKFILL_LIMIT and count >= BACKFILL_LIMIT:
                break
        await aconn.commit()

async def backfill_history():
    logging.info("Starting backfill: components + ACL + messages + mentions + reactions")
    async with apool.connection() as aconn:
        for g in bot.guilds:
            if GUILD_ID and str(g.id) != str(GUILD_ID):
                continue

            # preload/refresh identities for all members (idempotent)
            async with aconn.cursor(row_factory=dict_row) as cur:
                for m in g.members:
                    await cur.execute(
                        "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                        (ORG_ID, str(m.id), m.name),
                    )
            await aconn.commit()

            # enumerate and process each component once
            try:
                comps = []
                # enumerate_components is a normal function, not async generator
                for comp in await enumerate_components(g):
                    comps.append(comp)
            except TypeError:
                # if enumerate_components was written as generator (not awaited)
                comps = [comp async for comp in enumerate_components(g)]  # defensive

            for comp in comps:
                try:
                    await backfill_component(aconn, g, comp)
                except Exception:
                    logging.exception(f"Backfill failed for component {getattr(comp, 'name', comp.id)} in guild {g.name}")
                    continue
    logging.info("Backfill complete.")

# --------------------------
# Discord Event Handlers
# --------------------------

@bot.event
async def on_ready():
    global apool
    if apool is None:
        apool = AsyncConnectionPool(
            PG_DSN,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
        )
        await apool.open()

    if not bot.guilds:
        logging.warning("Connected but sees 0 guilds. Invite the bot to your server.")
    else:
        logging.info("Guilds visible:")
        for g in bot.guilds:
            logging.info(f"- {g.name} ({g.id})")

    # Prime known components
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            for g in bot.guilds:
                if GUILD_ID and str(g.id) != str(GUILD_ID):
                    continue
                for ch in g.channels:
                    try:
                        await upsert_component_row(cur, ch)
                    except Exception:
                        logging.exception(f"Component prime failed for {getattr(ch,'name',ch.id)}")
        await aconn.commit()

    if BACKFILL:
        await backfill_history()

    logging.info(f"Logged in as {bot.user} (guilds={len(bot.guilds)})")

@bot.event
async def on_guild_channel_create(channel):
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await upsert_component_row(cur, channel)
        await aconn.commit()
        await sync_component_access_latest(aconn, channel.guild, channel)
        await aconn.commit()

@bot.event
async def on_guild_channel_update(before, after):
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await upsert_component_row(cur, after)
        await aconn.commit()
        await sync_component_access_latest(aconn, after.guild, after)
        await aconn.commit()
        if isinstance(after, CategoryChannel):
            for ch in after.channels:
                await sync_component_access_latest(aconn, after.guild, ch)
            await aconn.commit()

@bot.event
async def on_guild_channel_delete(channel):
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
              delete from silver.component_members
              where system='discord' and component_id=%s
            """, (str(channel.id),))
        await aconn.commit()

@bot.event
async def on_thread_create(thread: Thread):
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await upsert_component_row(cur, thread)
        await aconn.commit()
        await sync_component_access_latest(aconn, thread.guild, thread)
        await aconn.commit()

@bot.event
async def on_thread_update(before: Thread, after: Thread):
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await upsert_component_row(cur, after)
        await aconn.commit()
        await sync_component_access_latest(aconn, after.guild, after)
        await aconn.commit()

@bot.event
async def on_guild_role_update(before, after):
    global _role_debounce
    now = time.time()
    if now - _role_debounce < 5:
        return
    _role_debounce = now

    async with apool.connection() as aconn:
        for ch in after.guild.channels:
            await sync_component_access_latest(aconn, after.guild, ch)
        await aconn.commit()

@bot.event
async def on_member_join(member):
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                (ORG_ID, str(member.id), member.name),
            )
        await aconn.commit()

@bot.event
async def on_member_update(before, after):
    async with apool.connection() as aconn:
        for ch in after.guild.channels:
            await sync_component_access_latest(aconn, after.guild, ch)
        await aconn.commit()

@bot.event
async def on_member_remove(member):
    try:
        async with apool.connection() as aconn:
            async with aconn.cursor(row_factory=dict_row) as cur:
                await cur.execute("""
                  update catalog.members m
                  set status='inactive', updated_at=now()
                  from catalog.member_identities mi
                  where mi.system='discord' and mi.external_id=%s and mi.member_id=m.member_id
                """, (str(member.id),))
            await aconn.commit()
    except Exception:
        logging.exception("on_member_remove error")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    created_at = message.created_at
    has_att = bool(message.attachments)

    raw = {
        "id": str(message.id),
        "channel_id": str(message.channel.id),
        "author_id": str(message.author.id),
        "content": message.content,
        "attachments": [a.url for a in message.attachments],
        "created_at": created_at.isoformat(),
    }

    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            # identity only (no auto-member)
            await cur.execute(
                "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                (ORG_ID, str(message.author.id), message.author.name),
            )
            await upsert_component_row(cur, message.channel)

            reply_to = (str(message.reference.message_id)
                        if message.reference and message.reference.message_id else None)

            author_member_id = await get_linked_member_id(cur, str(message.author.id))

            await cur.execute("""
                insert into silver.messages (
                    org_id, system, message_id, component_id, author_external_id, author_member_id,
                    content, has_attachments, reply_to_message_id, created_at_ts, raw
                )
                values (
                    %s,'discord',%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                on conflict (message_id) do update set
                  content=excluded.content,
                  has_attachments=excluded.has_attachments,
                  reply_to_message_id=excluded.reply_to_message_id,
                  raw=excluded.raw
            """, (
                ORG_ID, str(message.id), str(message.channel.id), str(message.author.id), author_member_id,
                message.content, has_att, reply_to, created_at, json.dumps(raw),
            ))
        await aconn.commit()

    await upsert_message_mentions(apool, message)

@bot.event
async def on_message_edit(before, after):
    raw = {
        "id": str(after.id),
        "content": after.content,
        "edited_at": utcnow().isoformat(),
    }
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "update silver.messages set content=%s, edited_at_ts=now(), raw=%s where message_id=%s",
                (after.content, json.dumps(raw), str(after.id)),
            )
        await aconn.commit()

    await upsert_message_mentions(apool, after)

@bot.event
async def on_raw_message_delete(payload):
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "update silver.messages set deleted_at_ts=now() where message_id=%s",
                (str(payload.message_id),),
            )
        await aconn.commit()

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.member and payload.member.bot:
        return
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            # ensure identity; then resolve link
            await cur.execute(
                "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                (ORG_ID, str(payload.user_id), payload.member.name if payload.member else str(payload.user_id)),
            )
            member_id = await get_linked_member_id(cur, str(payload.user_id))

            await cur.execute("""
                insert into silver.message_reactions (org_id, system, message_id, reaction, member_id, created_at_ts)
                values (%s, 'discord', %s, %s, %s, now())
                on conflict (message_id, reaction, member_id) do update
                    set created_at_ts = now(),        -- bump if re-added
                        updated_at_ts = now()
            """, (ORG_ID, str(payload.message_id), str(payload.emoji), member_id))
        await aconn.commit()

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
                select member_id from catalog.member_identities
                where system='discord' and external_id=%s
                limit 1
            """, (str(payload.user_id),))
            row = await cur.fetchone()
            member_id = get_member_id_from_row(row)

            if member_id:
                await cur.execute("""
                    delete from silver.message_reactions
                    where org_id=%s and system='discord'
                    and message_id=%s and reaction=%s and member_id=%s
                """, (ORG_ID, str(payload.message_id), str(payload.emoji), member_id))
        await aconn.commit()

# --------------------------
# Main
# --------------------------

def main():
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
