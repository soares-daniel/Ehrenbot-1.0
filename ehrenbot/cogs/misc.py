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

    @commands.slash_command(name="violin", description="Plays the worlds smallest violin")
    async def violin(self, ctx: discord.ApplicationContext):
        self.logger.info("%s used the violin command", ctx.author)
        if ctx.author.voice is None:
            await ctx.respond("You are not in a voice channel", ephemeral=True, delete_after=5)
        else:
            try:
                voice = await ctx.author.voice.channel.connect()
                await ctx.respond("https://tenor.com/view/sad-upset-violin-sponge-bob-mr-crab-gif-3466351", ephemeral=True, delete_after=15)
                voice.play(discord.FFmpegPCMAudio('data/mp3/violin.mp3'))
                while voice.is_playing():
                    await asyncio.sleep(1)
                await voice.disconnect()
            except Exception as ex:
                self.logger.error(ex)
                await ctx.respond("Something went wrong", ephemeral=True, delete_after=5)

    @commands.slash_command(name="select_character", description="Change your character symbol.")
    async def select_character(self, ctx):
        view = CharacterView()
        await ctx.respond("Select your character:", view=view)

def setup(bot):
    bot.add_cog(Misc(bot))
