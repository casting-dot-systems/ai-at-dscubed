"""
This file contains the UI components for the discord bot, including:
- Yes/No Button View
- Interaction check
"""

from typing import List, Optional

import discord

class YesNoView(discord.ui.View):
    def __init__(self, timeout: Optional[float], original_author: discord.Member | discord.User) -> None:
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.original_author: discord.Member | discord.User = original_author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.original_author

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        self.value = False
        await interaction.response.defer()
        self.stop()

class EngineSelectorView(discord.ui.View):
    def __init__(self, items: List[str], timeout: Optional[float] = 180.0):
        super().__init__(timeout=timeout)
        self.items = items
        self.selected_item: Optional[str] = None
        
        # Create buttons dynamically
        for i, item in enumerate(items):
            # Create a unique button for each item
            button : discord.ui.Button[discord.ui.View] = discord.ui.Button(
                label=item,
                style=discord.ButtonStyle.primary,
                custom_id=f"engine_{i}"
            )
            
            # Create a unique callback for each button
            async def button_callback(interaction: discord.Interaction, selected_item: str = item):
                await interaction.response.defer()
                self.selected_item = selected_item
                self.stop()
            
            button.callback = lambda i, item=item: button_callback(i, item)
            self.add_item(button)
    
    async def wait_for_selection(self) -> Optional[str]:
        """Wait for user to select an item and return the selected item"""
        await self.wait()
        return self.selected_item