import asyncio
import logging

import discord
from discord.ext import commands

from ehrenbot.utils.utils_misc import CharacterView


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

    @commands.slash_command(name="select_character", description="Change your character symbol.")
    async def select_character(self, ctx):
        view = CharacterView()
        await ctx.respond("Select your character:", view=view)

def setup(bot):
    bot.add_cog(Misc(bot))
