import logging

import discord
from discord.ext import commands

from ehrenbot.bot import Ehrenbot


class ClanAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

    clan_admin = discord.SlashCommandGroup(
        name="clan_admin", description="Clan admin commands."
    )

    @clan_admin.command(name="kick", description="Kick a member from the clan.")
    @commands.has_role("Clan Admin")
    async def kick(self, ctx: discord.ApplicationContext, member: discord.Member):
        member_collection = self.bot.database["members"]
        member = member_collection.find_one({"discord_id": member.id})
        if not member:
            await ctx.send(
                "The member you wanted to kick was not found. Please contact an admin."
            )
            return
        admin = member_collection.find_one({"discord_id": ctx.author.id})
        if not admin:
            await ctx.send(
                "Your Discord ID was not found in the database. Please contact an admin."
            )
            return
        token_collection = self.bot.database["destiny_tokens"]
        admin_token = token_collection.find_one({"discord_id": ctx.author.id})
        if not admin_token:
            await ctx.send(
                "Your Bungie.Net token was not found. Please contact an admin."
            )
            return
        membership_id = member["destiny_profile"]["membership_id"]
        membership_type = member["destiny_profile"]["membership_type"]
        admin_group_id = admin["destiny_profile"]["group_id"]
        response = await self.bot.destiny_client.group_v2.KickMember(
            token=admin_token,
            group_id=admin_group_id,
            membership_id=membership_id,
            membership_type=membership_type,
        )
        if response["ErrorCode"] != 1:
            await ctx.send(
                f"An error occurred while trying to kick the member. Please contact an admin.\n"
                f"Error code: {response['ErrorCode']}",
                hidden=True,
                delete_after=5,
            )
            # Notify bot_admin
            sedam = self.bot.get_user(self.bot.ADMIN_DISCORD_ID)
            await sedam.send(
                f"An error occurred while {ctx.author.name} tried to kick a member from the clan.\n"
                f"Response: {response}"
            )
            return
        if response["ErrorCode"] == 1:
            await ctx.send(
                f"Kicked {member.mention} from the clan.", hidden=True, delete_after=5
            )


def setup(bot):
    bot.add_cog(ClanAdmin(bot))
