import dotenv
import asyncio
import discord 
from discord.ext import commands
import os


dotenv.load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

class VoiceRecord(discord.VoiceClient):
    def __init__(self, bot, channel):
        super().__init__(bot, channel)
        self.user_audio_files = {}

    async def packets_handler(self, packet):
        user_id = packet.user_id
        data = packet.decrypted_data
        
        if user_id not in self.user_audio_files:
            f = open(f"user_{user_id}.pcm", "ab")
            self.user_audio_files[user_id] = f
        else:
            f = self.user_audio_files[user_id]
        f.write(data)

    async def disconnect(self):
        for user_id, f in self.user_audio_files.items():
            f.close()
        await super().disconnect()

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    vc = await channel.connect(cls=VoiceRecord)
    print(f"Connected to {channel}")

bot.run(TOKEN)