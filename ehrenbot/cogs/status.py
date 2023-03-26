# pylint: disable=E0211,E1121
import logging
from datetime import datetime

import discord
from discord.ext import commands, tasks

from ehrenbot import Ehrenbot
from ehrenbot.utils.utils_status import (
    check_api_status,
    check_group_v2_status,
    check_user_status,
    check_vendor_status,
)


class Status(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)
        self.api_status.start()

    def cog_unload(self) -> None:
        self.api_status.cancel()

    @tasks.loop(minutes=10)
    async def api_status(self):
        channel: discord.TextChannel = discord.utils.get(
            self.bot.get_all_channels(), name="⚙｜api-status"
        )
        if channel is None:
            return

        token_collection = self.bot.database["destiny_tokens"]
        profile_collection = self.bot.database["members"]
        token = token_collection.find_one({"discord_id": self.bot.ADMIN_DISCORD_ID})[
            "token"
        ]
        profile = profile_collection.find_one(
            {"discord_id": self.bot.ADMIN_DISCORD_ID}
        )["destiny_profile"]
        api_status = await check_api_status(self.bot)
        destiny_membership_id = profile["destiny_membership_id"]
        membership_type = profile["membership_type"]
        character_id = profile["character_ids"][0]
        vendor_status = await check_vendor_status(
            self.bot, destiny_membership_id, membership_type, character_id, token
        )
        user_status = await check_user_status(self.bot, 4611686018482584694, 3)
        group_v2_status = await check_group_v2_status(self.bot, 4751301)
        status = [api_status, vendor_status, user_status, group_v2_status]

        embed = discord.Embed(title="Bungie.Net API Status", color=0x2F3136)
        for stat in status:
            embed.add_field(name="\u200bStatus", value=stat["Status"], inline=True)
            embed.add_field(name="\u200bCategory", value=stat["Category"], inline=True)
            embed.add_field(
                name="\u200bUsed Endpoint", value=stat["Used Endpoint"], inline=True
            )
            time = datetime.utcnow()
        embed.set_footer(text=f"Last updated: {time.strftime('%d/%m/%Y %H:%M:%S')} UTC")
        embed.set_image(
            url="https://www.bungie.net/pubassets/pkgs/157/157031/D2_DPS_Gif.gif"
        )

        if channel.last_message_id is None:
            await channel.send(embed=embed)
        else:
            message = (await channel.history(limit=1).flatten())[0]
            await message.edit(content="", embed=embed)

    @api_status.before_loop
    async def before_api_status(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Status(bot))
