# app.py
import os, json, asyncio, logging, datetime as dt
import discord
from discord import TextChannel, Thread
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool
load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN   = os.getenv("DISCORD_WEBHOOK_BOT_KEY")
PG_DSN  = os.getenv("DATABASE_URL")
ORG_ID  = os.getenv("ORG_ID", "AI@DSCubed")
GUILDS  = [os.getenv("AI_AT_DSCUBED_GUILD_ID")]
FULL_LOAD = os.getenv("DISCORD_FULL_LOAD", "false").lower() == "true"

# Intents: members, messages, guilds, message content (if allowed)
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True


bot = discord.Client(intents=intents)

def utcnow():
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)

def jsonb(o):
    try:
        return json.loads(json.dumps(o, default=lambda x: getattr(x, "id", str(x))))
    except Exception:
        return None

def upsert_component(conn, component_id, component_type, name, parent_id, created_at=None, raw=None):
    conn.execute("""
      insert into silver.components (org_id, system, component_id, component_type, name, parent_component_id, created_at_ts, updated_at_ts, raw)
      values (%s,'discord',%s,%s,%s,%s,%s,%s,%s)
      on conflict (system, component_id) do update
        set component_type=excluded.component_type,
            name=excluded.name,
            parent_component_id=excluded.parent_component_id,
            updated_at_ts=excluded.updated_at_ts,
            raw=excluded.raw
    """, (ORG_ID, str(component_id), component_type, name, str(parent_id) if parent_id else None,
          created_at, utcnow(), jsonb(raw)))

def ensure_member(conn, discord_user):
    # calls the DB helper to ensure SSOT member + identity link
    with conn.cursor() as cur:
        cur.execute("select catalog.ensure_member_for_discord(%s,%s,%s)",
                    (ORG_ID, str(discord_user.id), discord_user.name))
        row = cur.fetchone()
        return row[0] if row else None

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

async def backfill_history():
    logging.info("Starting backfill…")
    async with apool.connection() as aconn:
        async with aconn.cursor() as cur:
            for g in bot.guilds:
                logging.info("Starting full load for guild %s", g.name)
                for ch in g.channels:
                    logging.info("Starting full load for channel %s", ch.name)
                    if isinstance(ch, (TextChannel, Thread)):
                        try:
                            async for msg in ch.history(limit=None, oldest_first=True):
                                # ensure component
                                ctype = type(msg.channel).__name__.lower()
                                parent = msg.channel.parent.id if getattr(msg.channel, "parent", None) else None
                                await cur.execute("""
                                  insert into silver.components (org_id, system, component_id, component_type, name, parent_component_id, created_at_ts, updated_at_ts)
                                  values (%s,'discord',%s,%s,%s,%s, now(), now())
                                  on conflict (system, component_id) do update set
                                    component_type=excluded.component_type,
                                    name=excluded.name,
                                    parent_component_id=excluded.parent_component_id,
                                    updated_at_ts=excluded.updated_at_ts
                                """, (ORG_ID, str(msg.channel.id), ctype, getattr(msg.channel, "name", str(msg.channel.id)),
                                      str(parent) if parent else None))

                                # ensure member + upsert message
                                raw = {
                                    "id": str(msg.id),
                                    "channel_id": str(msg.channel.id),
                                    "author_id": str(msg.author.id),
                                    "content": msg.content,
                                    "attachments": [a.url for a in msg.attachments],
                                    "created_at": msg.created_at.isoformat(),
                                }
                                await cur.execute("""
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
                                """, (ORG_ID, str(msg.author.id), msg.author.name,
                                      ORG_ID, str(msg.id), str(msg.channel.id), str(msg.author.id),
                                      msg.content, bool(msg.attachments),
                                      str(msg.reference.message_id) if msg.reference and msg.reference.message_id else None,
                                      msg.created_at, json.dumps(raw)))
                        except Exception:
                            logging.exception(f"Backfill failed for channel {ch} in guild {g.name}")
        await aconn.commit()
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
        async with aconn.cursor() as cur:
            for g in bot.guilds:
                for ch in g.channels:
                    try:
                        ctype = type(ch).__name__.lower()
                        parent = ch.parent.id if getattr(ch, "parent", None) else None
                        name = getattr(ch, "name", str(ch.id))
                        await cur.execute(
                            """
                            insert into silver.components (org_id, system, component_id, component_type, name, parent_component_id, created_at_ts, updated_at_ts)
                            values (%s,'discord',%s,%s,%s,%s, now(), now())
                            on conflict (system, component_id) do update set
                              component_type=excluded.component_type,
                              name=excluded.name,
                              parent_component_id=excluded.parent_component_id,
                              updated_at_ts=excluded.updated_at_ts
                            """,
                            (ORG_ID, str(ch.id), ctype, name, str(parent) if parent else None),
                        )
                    except Exception as e:
                        logging.exception(f"Component prime failed for {ch}: {e}")
        await aconn.commit()
    
    if FULL_LOAD:
        await backfill_history()
    logging.info(f"Logged in as {bot.user} (guilds={len(bot.guilds)})")

@bot.event
async def on_guild_channel_create(channel):
    ctype = type(channel).__name__.lower()
    parent = channel.parent.id if getattr(channel, "parent", None) else None
    name = getattr(channel, "name", str(channel.id))
    raw = {"id": str(channel.id), "name": name, "type": ctype, "parent_id": str(parent) if parent else None}

    async with apool.connection() as aconn:
        async with aconn.cursor() as cur:
            await cur.execute(
                """
                insert into silver.components (org_id, system, component_id, component_type, name, parent_component_id, created_at_ts, updated_at_ts, raw)
                values (%s,'discord',%s,%s,%s,%s, now(), now(), %s)
                on conflict (system, component_id) do update set
                  component_type=excluded.component_type,
                  name=excluded.name,
                  parent_component_id=excluded.parent_component_id,
                  updated_at_ts=excluded.updated_at_ts,
                  raw=excluded.raw
                """,
                (ORG_ID, str(channel.id), ctype, name, str(parent) if parent else None, json.dumps(raw)),
            )
        await aconn.commit()


@bot.event
async def on_thread_create(thread):
    # threads are components too
    await on_guild_channel_create(thread)

@bot.event
async def on_member_join(member):
    async with apool.connection() as aconn:
        async with aconn.cursor() as cur:
            await cur.execute(
                "select catalog.ensure_member_for_discord(%s,%s,%s)",
                (ORG_ID, str(member.id), member.name),
            )
        await aconn.commit()


@bot.event
async def on_member_remove(member):
    try:
        async with apool.connection() as aconn:
            async with aconn.cursor() as cur:
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

    ctype = type(message.channel).__name__.lower()
    parent = message.channel.parent.id if getattr(message.channel, "parent", None) else None
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
        async with aconn.cursor() as cur:
            # ensure component
            await cur.execute(
                """
                insert into silver.components (org_id, system, component_id, component_type, name, parent_component_id, created_at_ts, updated_at_ts)
                values (%s,'discord',%s,%s,%s,%s, now(), now())
                on conflict (system, component_id) do update set
                  component_type=excluded.component_type,
                  name=excluded.name,
                  parent_component_id=excluded.parent_component_id,
                  updated_at_ts=excluded.updated_at_ts
                """,
                (ORG_ID, str(message.channel.id), ctype, getattr(message.channel, "name", str(message.channel.id)),
                 str(parent) if parent else None),
            )

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


@bot.event
async def on_message_edit(before, after):
    raw = {
        "id": str(after.id),
        "content": after.content,
        "edited_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    async with apool.connection() as aconn:
        async with aconn.cursor() as cur:
            await cur.execute(
                "update silver.messages set content=%s, edited_at_ts=now(), raw=%s where message_id=%s",
                (after.content, json.dumps(raw), str(after.id)),
            )
        await aconn.commit()

@bot.event
async def on_raw_message_delete(payload):
    async with apool.connection() as aconn:
        async with aconn.cursor() as cur:
            await cur.execute(
                "update silver.messages set deleted_at_ts=now() where message_id=%s",
                (str(payload.message_id),),
            )
        await aconn.commit()

if __name__ == "__main__":
    bot.run(TOKEN)
