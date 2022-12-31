import logging
import os

import discord
from discord.ext import commands

from ehrenbot.bot import Ehrenbot


class Owner(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

    owner = discord.SlashCommandGroup(name="owner", description="Owner commands.")

    def get_cogs(self) -> list:
        return [cog.replace(".py", "") for cog in os.listdir("ehrenbot/cogs") if cog.endswith(".py")]

    @owner.command(name="reload", description="Reload a cog.")
    @commands.is_owner()
    async def reload(self, ctx, cog: discord.Option(str, autocomplete=get_cogs)):
        """ Reload a cog """
        self.bot.reload_extension(f"ehrenbot.cogs.{cog}")
        await ctx.respond(f"Reloaded {cog}", delete_after=5)

    @owner.command(name="load", description="Load a cog.")
    @commands.is_owner()
    async def load(self, ctx, cog: discord.Option(str, autocomplete=get_cogs)):
        """ Load a cog """
        self.bot.load_extension(f"ehrenbot.cogs.{cog}")
        await ctx.respond(f"Loaded {cog}", delete_after=5)

    @owner.command(name="unload", description="Unload a cog.")
    @commands.is_owner()
    async def unload(self, ctx, cog: discord.Option(str, autocomplete=get_cogs)):
        """ Unload a cog """
        self.bot.unload_extension(f"ehrenbot.cogs.{cog}")
        await ctx.respond(f"Unloaded {cog}", delete_after=5)

def setup(bot) -> None:
    bot.add_cog(Owner(bot))
