import discord
from discord.ext import commands
from fastapi import FastAPI


def setup_slash_commands(bot: commands.Bot) -> None:
    """Set up slash commands for the bot."""

    @bot.tree.command(
        name="connect", description="Create a new session and form stable connection"
    )
    async def connect(interaction: discord.Interaction, user: discord.Member): # type: ignore
        """Slash command to create a new session and form stable connection."""
        try:
            fastapi_app = FastAPI()

            await interaction.response.send_message(
                f"✅ Scrum checkup initiated for {user.mention}!", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to initiate scrum checkup: {str(e)}", ephemeral=True
            )