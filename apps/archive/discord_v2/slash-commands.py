import discord
from discord.ext import commands
from fastapi import FastAPI


def setup_slash_commands(bot: commands.Bot) -> None:
    """Set up slash commands for the bot."""

    @self.bot.tree.command(
        name="connect", description="Create a new session and form stable connection"
    )
    async def connect(interaction: discord.Interaction): # type: ignore
        """Slash command to create a new session and form stable connection."""
        try:
            response = await self.api_client.create_session()

            await interaction.response.send_message(
                f"✅ Session created! Session ID: {response.session_id}", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to create session: {str(e)}", ephemeral=True
            )