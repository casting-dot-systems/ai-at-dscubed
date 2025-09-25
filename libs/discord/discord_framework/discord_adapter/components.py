from __future__ import annotations

import asyncio
from typing import Optional

import discord


class YesNoView(discord.ui.View):
    def __init__(self, timeout: Optional[float], original_author: discord.abc.User) -> None:
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.original_author = original_author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.original_author.id

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction, _: discord.ui.Button[discord.ui.View]) -> None:
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction: discord.Interaction, _: discord.ui.Button[discord.ui.View]) -> None:
        self.value = False
        await interaction.response.defer()
        self.stop()


class TextInputModal(discord.ui.Modal, title="Provide input"):
    def __init__(self, prompt: str) -> None:
        super().__init__(timeout=None)
        self.value: Optional[str] = None
        self.input = discord.ui.TextInput(
            label="Input",
            placeholder=prompt,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1900,
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.value = str(self.input.value)
        await interaction.response.defer()
        self.stop()


class TextPromptView(discord.ui.View):
    """A button that opens a modal to collect multi-line text."""
    def __init__(self, timeout: Optional[float], original_author: discord.abc.User, prompt: str) -> None:
        super().__init__(timeout=timeout)
        self.value: Optional[str] = None
        self.original_author = original_author
        self.prompt = prompt

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.original_author.id

    @discord.ui.button(label="Open prompt", style=discord.ButtonStyle.blurple)
    async def open_modal(self, interaction: discord.Interaction, _: discord.ui.Button[discord.ui.View]) -> None:
        modal = TextInputModal(self.prompt)
        await interaction.response.send_modal(modal)
        try:
            await asyncio.wait_for(modal.wait(), timeout=self.timeout or 60)
        except asyncio.TimeoutError:
            self.value = None
            self.stop()
            return
        self.value = modal.value
        self.stop()