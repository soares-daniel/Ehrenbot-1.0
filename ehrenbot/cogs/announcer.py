import logging

import discord
from discord.ext import commands

from ehrenbot.bot import Ehrenbot


class Announcer(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

    announce = discord.SlashCommandGroup(name="announce", description="Announcer commands.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.name == "ehrenbot-updates-sedam":
            channel = discord.utils.get(message.guild.channels, name="ehrenbot-updates")
            if not channel:
                return
            await channel.send(message.content)
        if message.channel.name == "server-announcements-sedam":
            channel = discord.utils.get(message.guild.channels, name="server-announcements")
            if not channel:
                return
            await channel.send(message.content)

def setup(bot) -> None:
    bot.add_cog(Announcer(bot))
