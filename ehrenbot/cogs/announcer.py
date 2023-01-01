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
        channel = None
        if message.channel.name == "ehrenbot-updates-sedam":
            channel = discord.utils.get(message.guild.channels, name="ehrenbot-updates")
        if message.channel.name == "server-announcements-sedam":
            channel = discord.utils.get(message.guild.channels, name="server-announcements")
        if not channel:
            return
        await channel.send(message.content)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        channel = None
        if before.channel.name == "ehrenbot-updates-sedam":
            channel: discord.TextChannel = discord.utils.get(before.guild.channels, name="ehrenbot-updates")
        if before.channel.name == "server-announcements-sedam":
            channel: discord.TextChannel = discord.utils.get(before.guild.channels, name="server-announcements")
        if not channel:
            return
        #look through the messages in the channel and find the one that matches with the old content
        async for message in channel.history(limit=100):
            if message.content == before.content:
                await message.edit(content=after.content)
                return
def setup(bot) -> None:
    bot.add_cog(Announcer(bot))
