import os, json, asyncio, logging, time, datetime as dt
import discord
from discord import TextChannel, Thread, VoiceChannel, ForumChannel, CategoryChannel, StageChannel
from typing import Iterable
from psycopg.rows import dict_row
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool
import logging
from contextlib import asynccontextmanager

load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN   = os.getenv("DISCORD_WEBHOOK_BOT_KEY")
PG_DSN  = os.getenv("DATABASE_URL")
ORG_ID  = os.getenv("ORG_ID", "AI@DSCubed")
GUILDS  = [os.getenv("AI_AT_DSCUBED_GUILD_ID")]
BACKFILL = os.getenv("DISCORD_BACKFILL", "false").lower() == "true"
BACKFILL_LIMIT = int(os.getenv("DISCORD_BACKFILL_LIMIT", "0") or 0)  # 0 = no limit

CHANNEL_TYPES = (TextChannel, Thread, VoiceChannel, ForumChannel, CategoryChannel, StageChannel)

# Intents: members, messages, guilds, message content (if allowed)
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True


bot = discord.Client(intents=intents)

async def log_and_raise(sql: str, params, err: Exception):
    logging.error("SQL failed: %s\nparams=%r\nerror=%r", sql, params, err)
    raise

@asynccontextmanager
async def tx(aconn):
    try:
        async with aconn.transaction():  # psycopg3 async tx scope
            yield
    except Exception as e:
        # connection is auto-rolled back by the tx CM; just re-raise
        raise

def classify_component(obj) -> tuple[str, str | None]:
    """
    Returns (component_type, parent_component_id)
    Types: 'guild_text','thread','forum','forum_post','voice','category','stage'
    """
    if isinstance(obj, ForumChannel):
        return ("forum", None)
    if isinstance(obj, Thread):
        # forum posts are threads whose parent is a ForumChannel
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
    # fallback
    return (type(obj).__name__.lower(), None)

def utcnow():
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)

def jsonb(o):
    try:
        return json.loads(json.dumps(o, default=lambda x: getattr(x, "id", str(x))))
    except Exception:
        return None

async def upsert_component_row(cur, obj, name_hint=None, raw=None):
    ctype, parent_id = classify_component(obj)
    name = getattr(obj, "name", name_hint or str(obj.id))
    await cur.execute("""
      insert into silver.components (org_id, system, component_id, component_type, name, parent_component_id, created_at_ts, updated_at_ts, raw)
      values (%s,'discord',%s,%s,%s,%s, now(), now(), %s)
      on conflict (system, component_id) do update set
        component_type=excluded.component_type,
        name=excluded.name,
        parent_component_id=excluded.parent_component_id,
        updated_at_ts=excluded.updated_at_ts,
        raw=excluded.raw
    """, (ORG_ID, str(obj.id), ctype, name, str(parent_id) if parent_id else None, json.dumps(raw) if raw else None))

def ensure_member(conn, discord_user):
    # calls the DB helper to ensure SSOT member + identity link
    with conn.cursor() as cur:
        cur.execute("select catalog.ensure_member_for_discord(%s,%s,%s)",
                    (ORG_ID, str(discord_user.id), discord_user.name))
        row = cur.fetchone()
        return get_member_id_from_row(row)

def upsert_message(conn, message, deleted_at=None, edited_at=None):
    author_id = str(message.author.id)
    member_id = ensure_member(conn, message.author)

    reply_to = str(message.reference.message_id) if message.reference and message.reference.message_id else None
    has_att = bool(message.attachments)
    created_at = message.created_at if message.created_at.tzinfo else message.created_at.replace(tzinfo=dt.timezone.utc)

    conn.execute("""
      insert into silver.messages (org_id, system, message_id, component_id, author_external_id, author_member_id,
                                   content, has_attachments, reply_to_message_id, created_at_ts, edited_at_ts, deleted_at_ts, raw)
      values (%s,'discord',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
      on conflict (message_id) do update
        set content=excluded.content,
            has_attachments=excluded.has_attachments,
            reply_to_message_id=excluded.reply_to_message_id,
            edited_at_ts=coalesce(excluded.edited_at_ts, silver.messages.edited_at_ts),
            deleted_at_ts=coalesce(excluded.deleted_at_ts, silver.messages.deleted_at_ts),
            raw=excluded.raw
    """, (ORG_ID, str(message.id), str(message.channel.id), author_id, member_id,
          message.content, has_att, reply_to, created_at, edited_at, deleted_at, jsonb(message.to_dict())))

async def upsert_message_mentions(aconn, msg: discord.Message):
    # Gather mentions
    rows = []
    # User mentions
    for u in msg.mentions:  # discord.Member/User objects
        rows.append(("user", str(u.id)))
    # Role mentions
    for r in getattr(msg, "role_mentions", []):
        rows.append(("role", str(r.id)))
    # Channel mentions (e.g., #general)
    for ch in getattr(msg, "channel_mentions", []):
        rows.append(("channel", str(ch.id)))
    # Everyone/here
    if getattr(msg, "mention_everyone", False):
        rows.append(("everyone", None))
        # discord doesn't separately flag @here, but you can detect text if needed:
        if "@here" in (msg.content or ""):
            rows.append(("here", None))

    async with aconn.cursor(row_factory=dict_row) as cur:
        # wipe existing mentions for idempotency
        await cur.execute("delete from silver.message_mentions where message_id=%s", (str(msg.id),))
        if not rows:
            return

        # Resolve member_ids for user mentions
        values = []
        for mtype, ext in rows:
            member_uuid = None
            if mtype == "user" and ext:
                await cur.execute("""
                  select mi.member_id
                  from catalog.member_identities mi
                  where mi.system='discord' and mi.external_id=%s
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

def get_member_id_from_row(row):
    if row is None:
        return None
    # psycopg row can be a dict (dict_row) or a tuple depending on row_factory
    if isinstance(row, dict):
        return row.get("member_id")
    # fallback: positional
    try:
        return row[0]
    except Exception:
        return None

async def resolve_member_uuid(cur, discord_user_id: str):
    await cur.execute(
        """
        select member_id
        from catalog.member_identities
        where system = 'discord' and external_id = %s
        limit 1
        """,
        (discord_user_id,),
    )
    row = await cur.fetchone()
    return get_member_id_from_row(row)

async def current_viewers(guild: discord.Guild, channel) -> list[discord.Member]:
    # Requires Intents.members and member cache
    viewers = []
    for m in guild.members:
        try:
            if channel.permissions_for(m).view_channel:
                viewers.append(m)
        except Exception:
            # Some channel types / partial perms can throw, ignore gracefully
            pass
    return viewers

async def sync_component_access_latest(aconn, guild: discord.Guild, channel):
    """
    Bring silver.component_members to the latest truth for this component:
      - UPSERT all current viewers with can_view=True
      - DELETE rows for external_ids no longer present
    """
    if isinstance(channel, CategoryChannel):
        # Optional: skip categories if you only care about message-bearing components
        return

    async with aconn.cursor(row_factory=dict_row) as cur:
        # Compute current set
        viewers = await current_viewers(guild, channel)
        current = {str(m.id): m for m in viewers}

        # Ensure identities exist (no auto member)
        for m in viewers:
            await cur.execute(
                "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                (ORG_ID, str(m.id), m.display_name or m.name),
            )

        # Load existing rows for this component
        await cur.execute("""
          select external_id
          from silver.component_members
          where system='discord' and component_id=%s
        """, (str(channel.id),))
        existing = {get_member_id_from_row(row) for row in await cur.fetchall()}

        # Upserts for new/changed
        upserts = []
        for ext_id, member in current.items():
            member_uuid = await resolve_member_uuid(cur, ext_id)
            upserts.append((
                'discord', str(channel.id), ext_id, member_uuid, True, ORG_ID
            ))

        if upserts:
            await cur.executemany("""
              insert into silver.component_members (system, component_id, external_id, member_id, can_view, org_id, updated_at_ts)
              values (%s,%s,%s,%s,%s,%s, now())
              on conflict (system, component_id, external_id) do update
                set member_id = excluded.member_id,
                    can_view  = excluded.can_view,
                    org_id    = excluded.org_id,
                    updated_at_ts = now()
            """, upserts)

        # Deletes for stale
        stale_ext_ids = existing - set(current.keys())
        if stale_ext_ids:
            await cur.executemany("""
              delete from silver.component_members
              where system='discord' and component_id=%s and external_id=%s
            """, [(str(channel.id), ext) for ext in stale_ext_ids])

async def snapshot_component_access(aconn, guild: discord.Guild, channel):
    # Skip categories if you want only message-bearing components
    if isinstance(channel, CategoryChannel):
        return
    # We need guild.members; requires Intents.members and member cache
    viewers: list[discord.Member] = []
    for m in guild.members:
        perms = channel.permissions_for(m)
        if perms.view_channel:
            viewers.append(m)

    async with aconn.cursor(row_factory=dict_row) as cur:
        # Insert one snapshot row per viewer (keep historical snapshots)
        rows = []
        for m in viewers:
            # ensure identity row exists but don't link member_id
            await cur.execute("select catalog.ensure_identity_for_discord(%s,%s,%s)",
                              (ORG_ID, str(m.id), m.display_name or m.name))
            # resolve to member_id if already linked
            await cur.execute("""
              select member_id from catalog.member_identities
              where system='discord' and external_id=%s
            """, (str(m.id),))
            r = await cur.fetchone()
            member_uuid = get_member_id_from_row(r)
            rows.append(('discord', str(channel.id), member_uuid, str(m.id), True, ORG_ID))

        if rows:
            await cur.executemany("""
              insert into silver.component_members (system, component_id, member_id, external_id, can_view, org_id)
              values (%s,%s,%s,%s,%s,%s)
            """, rows)

async def backfill_forum_posts(aconn, forum: ForumChannel):
    """
    Ensure the forum (container) and all its posts (threads) exist as components.
    Handles:
      - active posts: forum.threads
      - archived posts: forum.archived_threads(...) async iterator
    """
    # 0) Upsert the forum container itself (if you haven't already)
    async with aconn.cursor() as cur:
        await upsert_component_row(cur, forum)
    await aconn.commit()

    # 1) Active posts (already-loaded list)
    if forum.threads:
        async with aconn.cursor() as cur:
            for t in forum.threads:
                await upsert_component_row(cur, t)
        await aconn.commit()

    # 2) Archived posts — async iterator (DON'T await it; iterate it)
    # Use 'before' to paginate; each call returns a new iterator.
    before = None  # can be a Thread or datetime; Thread works fine here
    while True:
        fetched = 0
        async for t in forum.archived_threads(limit=100, before=before):
            # each 't' is a Thread representing a forum post
            async with aconn.cursor() as cur:
                await upsert_component_row(cur, t)
            fetched += 1
            before = t  # paginate based on the last thread seen
        await aconn.commit()
        if fetched == 0:
            break

async def backfill_history():
    logging.info("Starting backfill: identities + components + messages + mentions + ACL snapshots")
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            for g in bot.guilds:
                # 1) identities for all guild members (no truncation; idempotent)
                for m in g.members:
                    await cur.execute(
                        "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                        (ORG_ID, str(m.id), m.display_name or m.name),
                    )
                await aconn.commit()

                # 2) components + ACL snapshots
                for ch in g.channels:
                    try:
                        await upsert_component_row(cur, ch)
                        await aconn.commit()

                        # latest ACL for the container itself (forum/channel/thread)
                        await sync_component_access_latest(aconn, g, ch)
                        await aconn.commit()

                        # if it's a forum, also ensure all posts (threads) exist
                        if isinstance(ch, ForumChannel):
                            await backfill_forum_posts(aconn, ch)
                            # and ACL for each post
                            for t in ch.threads:
                                await sync_component_access_latest(aconn, g, t)
                            await aconn.commit()

                        # message history: TextChannel & Thread (includes forum posts)
                        if isinstance(ch, (TextChannel, Thread)):
                            count = 0
                            async for msg in ch.history(limit=None, oldest_first=True):
                                # ensure identity row for author
                                await cur.execute(
                                    "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                                    (ORG_ID, str(msg.author.id), msg.author.display_name or msg.author.name),
                                )
                                # upsert message (same as your live handler)
                                await cur.execute("""
                                  with ensured as (
                                    select member_id from catalog.member_identities
                                    where system='discord' and external_id=%s
                                  )
                                  insert into silver.messages (
                                    org_id, system, message_id, component_id, author_external_id, author_member_id,
                                    content, has_attachments, reply_to_message_id, created_at_ts, raw
                                  )
                                  values (
                                    %s,'discord',%s,%s,%s,(select member_id from ensured),
                                    %s,%s,%s,%s,%s
                                  )
                                  on conflict (message_id) do update set
                                    content=excluded.content,
                                    has_attachments=excluded.has_attachments,
                                    reply_to_message_id=excluded.reply_to_message_id,
                                    raw=excluded.raw
                                """, (
                                    str(msg.author.id),
                                    ORG_ID, str(msg.id), str(msg.channel.id), str(msg.author.id),
                                    msg.content, bool(msg.attachments),
                                    str(msg.reference.message_id) if msg.reference and msg.reference.message_id else None,
                                    msg.created_at, json.dumps({
                                        "id": str(msg.id),
                                        "channel_id": str(msg.channel.id),
                                        "author_id": str(msg.author.id),
                                        "created_at": msg.created_at.isoformat(),
                                    })
                                ))
                                count += 1
                                if BACKFILL_LIMIT and count >= BACKFILL_LIMIT:
                                    break
                            await aconn.commit()

                            # mentions per message: re-read latest N (or all if cheap)
                            async for msg in ch.history(limit=BACKFILL_LIMIT or 5000, oldest_first=False):
                                await upsert_message_mentions(aconn, msg)
                            await aconn.commit()
                            
                            # backfill reactions for messages in this channel
                            logging.info(f"Backfilling reactions for channel {ch.name}")
                            reaction_count = await backfill_reactions(aconn, ch, limit=BACKFILL_LIMIT)
                            logging.info(f"Backfilled reactions for {reaction_count} messages in {ch.name}")
                    except Exception:
                        logging.exception(f"Backfill failed for channel {ch} in guild {g.name}")
    logging.info("Backfill complete.")

apool: AsyncConnectionPool | None = None

@bot.event
async def on_ready():
    global apool
    if apool is None:
        apool = AsyncConnectionPool(
            PG_DSN,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row}
        )
        await apool.open()  # <<< IMPORTANT

    # Log what Discord actually gave you
    if not bot.guilds:
        logging.warning("Bot is connected but sees 0 guilds. Did you invite it to your server?")
    else:
        logging.info("Guilds visible:")
        for g in bot.guilds:
            logging.info(f"- {g.name} ({g.id})")

    # Prime components only for guilds we actually see
    async with apool.connection() as aconn:        
        async with aconn.cursor(row_factory=dict_row) as cur:
            for g in bot.guilds:
                for ch in g.channels:
                    try:
                        await upsert_component_row(cur, ch)
                    except Exception as e:
                        logging.exception(f"Component prime failed for {ch}: {e}")
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
        # keep component metadata fresh
        async with aconn.cursor() as cur:
            await upsert_component_row(cur, after)
        await aconn.commit()

        # resync ACL for the channel/thread/forum itself
        await sync_component_access_latest(aconn, after.guild, after)
        await aconn.commit()

        # if a category changed, children inherit → resync all children
        if isinstance(after, CategoryChannel):
            for ch in after.channels:
                await sync_component_access_latest(aconn, after.guild, ch)
            await aconn.commit()

@bot.event
async def on_guild_channel_delete(channel):
    # channel removed → remove its ACL rows
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""
              delete from silver.component_members
              where system='discord' and component_id=%s
            """, (str(channel.id),))
        await aconn.commit()

@bot.event
async def on_guild_role_update(before, after):
    global _role_debounce
    now = time.time()
    if now - _role_debounce < 5:  # 5s debounce
        return
    _role_debounce = now

    async with apool.connection() as aconn:
        for ch in after.guild.channels:
            await sync_component_access_latest(aconn, after.guild, ch)
        await aconn.commit()

@bot.event
async def on_thread_create(thread):
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await upsert_component_row(cur, thread)
        await aconn.commit()
    # keep ACL in sync
    async with apool.connection() as aconn:
        await sync_component_access_latest(aconn, thread.guild, thread)
        await aconn.commit()

@bot.event
async def on_thread_update(before: Thread, after: Thread):
    async with apool.connection() as aconn:
        async with aconn.cursor() as cur:
            await upsert_component_row(cur, after)
        await aconn.commit()
        await sync_component_access_latest(aconn, after.guild, after)
        await aconn.commit()

@bot.event
async def on_member_join(member):
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                (ORG_ID, str(member.id), member.display_name or member.name),
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

    reply_to = str(message.reference.message_id) if message.reference and message.reference.message_id else None
    created_at = message.created_at  # discord.py provides aware UTC datetimes
    has_att = bool(message.attachments)
    # Minimal raw snapshot (discord.py doesn't guarantee .to_dict())
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
            # ensure identity (no auto-member)
            await cur.execute(
                "select catalog.ensure_identity_for_discord(%s,%s,%s)",
                (ORG_ID, str(message.author.id), message.author.display_name or message.author.name),
            )
            # ensure component
            await upsert_component_row(cur, message.channel)

            # ensure member + upsert message
            await cur.execute(
                """
                with ensured as (
                    select catalog.ensure_member_for_discord(%s,%s,%s) as member_id
                )
                insert into silver.messages (
                    org_id, system, message_id, component_id, author_external_id, author_member_id,
                    content, has_attachments, reply_to_message_id, created_at_ts, raw
                )
                values (
                    %s,'discord',%s,%s,%s,(select member_id from ensured),
                    %s,%s,%s,%s,%s
                )
                on conflict (message_id) do update set
                  content=excluded.content,
                  has_attachments=excluded.has_attachments,
                  reply_to_message_id=excluded.reply_to_message_id,
                  raw=excluded.raw
                """,
                (
                    ORG_ID, str(message.author.id), message.author.name,
                    ORG_ID, str(message.id), str(message.channel.id), str(message.author.id),
                    message.content, has_att, reply_to, created_at, json.dumps(raw),
                ),
            )
        await aconn.commit()
        # mentions (after commit so message row exists)
        await upsert_message_mentions(aconn, message)
        await aconn.commit()


@bot.event
async def on_message_edit(before, after):
    raw = {
        "id": str(after.id),
        "content": after.content,
        "edited_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "update silver.messages set content=%s, edited_at_ts=now(), raw=%s where message_id=%s",
                (after.content, json.dumps(raw), str(after.id)),
            )
        await aconn.commit()
        await upsert_message_mentions(aconn, after)
        await aconn.commit()

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
    """Handle real-time reaction additions."""
    if payload.member and payload.member.bot:
        return  # Skip bot reactions
    
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            # Ensure member exists and get member_id
            await cur.execute(
                "select catalog.ensure_member_for_discord(%s,%s,%s) as member_id",
                (ORG_ID, str(payload.user_id), payload.member.name if payload.member else str(payload.user_id))
            )
            row = await cur.fetchone()
            member_id = get_member_id_from_row(row)
            
            # Insert or update reaction
            await cur.execute("""
                insert into silver.reactions (message_id, reaction, member_id, created_at_ts)
                values (%s, %s, %s, now())
                on conflict (message_id, reaction, member_id) do update
                    set created_at_ts = now()
            """, (str(payload.message_id), str(payload.emoji), member_id))
        await aconn.commit()

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Handle real-time reaction removals."""
    async with apool.connection() as aconn:
        async with aconn.cursor(row_factory=dict_row) as cur:
            # Get member_id for the user
            await cur.execute("""
                select member_id from catalog.member_identities
                where system='discord' and external_id=%s
            """, (str(payload.user_id),))
            row = await cur.fetchone()
            member_id = get_member_id_from_row(row)
            
            if member_id:
                # Delete the reaction
                await cur.execute("""
                    delete from silver.reactions 
                    where message_id=%s and reaction=%s and member_id=%s
                """, (str(payload.message_id), str(payload.emoji), member_id))
        await aconn.commit()

async def backfill_reactions(aconn, channel, limit=None):
    """Backfill reactions for messages in a channel."""
    count = 0
    async for msg in channel.history(limit=limit, oldest_first=True):
        if not msg.reactions:
            continue
            
        for reaction in msg.reactions:
            # Fetch all users who reacted with this emoji
            async for user in reaction.users():
                if user.bot:
                    continue
                
                async with aconn.cursor(row_factory=dict_row) as cur:
                    # Ensure member exists and get member_id
                    await cur.execute(
                        "select catalog.ensure_member_for_discord(%s,%s,%s) as member_id",
                        (ORG_ID, str(user.id), user.name)
                    )
                    row = await cur.fetchone()
                    member_id = get_member_id_from_row(row)
                    
                    # Insert reaction (using message created_at as approximate reaction time for backfill)
                    await cur.execute("""
                        insert into silver.reactions (message_id, reaction, member_id, created_at_ts)
                        values (%s, %s, %s, %s)
                        on conflict (message_id, reaction, member_id) do nothing
                    """, (str(msg.id), str(reaction.emoji), member_id, msg.created_at))
                    
        count += 1
        if limit and count >= limit:
            break
    
    await aconn.commit()
    return count

if __name__ == "__main__":
    bot.run(TOKEN)
