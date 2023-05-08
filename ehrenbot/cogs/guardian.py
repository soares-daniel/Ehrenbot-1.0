import logging

import discord
from discord.ext import commands

from ehrenbot import Ehrenbot


class Guardian(commands.Cog):
    def __init__(self, bot: Ehrenbot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)
        self.update_profiles.start()

    def cog_unload(self) -> None:
        self.update_profiles.cancel()

    guardian = discord.SlashCommandGroup(
        name="guardian",
        description="Commands for interacting with your Destiny 2 Guardian.",
    )

    @guardian.command(name="profile", description="View your Destiny 2 profile.")
    async def guardian_profile(self, ctx: discord.ApplicationContext):
        """View your Destiny 2 profile."""

    @guardian.command(name="inventory", description="View your Destiny 2 inventory.")
    async def guardian_inventory(self, ctx: discord.ApplicationContext):
        """View your Destiny 2 inventory."""


def setup(bot) -> None:
    bot.add_cog(Guardian(bot))
