import logging

import discord
from discord.ext import commands, tasks

from ehrenbot.bot import Ehrenbot


class ChannelManager(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)
        temp_channels = self.bot.database["temp_channels"].find_one(
            {"channel_type": "voice_channels"}
        )
        if temp_channels:
            self.temp_channels = temp_channels["channels"]
        else:
            self.temp_channels = []
        self.delete_temp_channels.start()

    def cog_unload(self) -> None:
        self.delete_temp_channels.cancel()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Manage temporary voice channels"""
        # Create a temporary channel if the user joins a channel and the channel starts with "New"
        if after.channel:
            if after.channel.name.lower().startswith("New".lower()):
                if after.channel.id not in self.temp_channels:
                    channel_name = after.channel.name.replace("New ", "")
                    temp_channel = await after.channel.clone(
                        name=f"{member.display_name}'s {channel_name}"
                    )
                    await member.move_to(temp_channel)
                    self.temp_channels.append(temp_channel.id)

        # Delete the temporary channel if the user leaves the channel
        if before.channel:
            if before.channel.id in self.temp_channels:
                if len(before.channel.members) == 0:
                    await before.channel.delete()
                    self.temp_channels.remove(before.channel.id)

        self.bot.database["temp_channels"].update_one(
            {"channel_type": "voice_channels"},
            {"$set": {"channels": self.temp_channels}},
            upsert=True,
        )

    @tasks.loop(count=1)
    async def delete_temp_channels(self):
        for channel_id in self.temp_channels:
            channel = self.bot.get_channel(channel_id)
            if channel:
                if len(channel.members) == 0:
                    await channel.delete()
                    self.temp_channels.remove(channel_id)

        self.bot.database["temp_channels"].update_one(
            {"channel_type": "voice_channels"},
            {"$set": {"channels": self.temp_channels}},
            upsert=True,
        )

    @delete_temp_channels.before_loop
    async def before_delete_temp_channels(self):
        await self.bot.wait_until_ready()


def setup(bot) -> None:
    bot.add_cog(ChannelManager(bot))
