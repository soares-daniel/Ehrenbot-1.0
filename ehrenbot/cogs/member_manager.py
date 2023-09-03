import csv
import logging
from typing import Dict

import discord
from discord.ext import commands, tasks

from ehrenbot.bot import Ehrenbot


class MemberManager(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)
        self.invites: Dict[int, list[discord.Invite]] = {}
        self.get_invites.start()

    @tasks.loop(seconds=60, count=1)
    async def get_invites(self):
        for guild in self.bot.guilds:
            self.invites[guild.id] = await guild.invites()

    @get_invites.before_loop
    async def before_get_invites(self):
        await self.bot.wait_until_ready()

    def find_invite_by_code(
        self, inv_list: list[discord.Invite], code: str
    ) -> discord.Invite:
        """Find an invite by its code"""
        for invite in inv_list:
            if invite.code == code:
                return invite

    async def get_latest_invite_code(self, member: discord.Member) -> str:
        """Get the invite code of the latest invite used by a member"""
        invites_before = self.invites[member.guild.id]
        invites_after = await member.guild.invites()
        self.invites[member.guild.id] = invites_after
        for invite in invites_before:
            if invite.uses < self.find_invite_by_code(invites_after, invite.code).uses:
                return invite.code

    @commands.slash_command(
        name="setup_members", description="Setup the member hall."
    )
    async def setup_members(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        members = ctx.guild.members
        # sort members by join date
        members.sort(key=lambda x: x.joined_at)
        for member in members:
            embed = discord.Embed(title=f"{member.display_name}")
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(
                name="User Info",
                value=f"<@{member.id}> \n**ID**: {member.id}",
                inline=False,
            )
            invite_code = await self.get_latest_invite_code(member=member)
            if not invite_code or invite_code == []:
                invite_code = "YJmhrdcHnX"
                if member.id == self.bot.ADMIN_DISCORD_ID:
                    invite_code = "OWNER"
                if ctx.guild.id == self.bot.DEBUG_GUILD_ID:
                    invite_code = "None"
            embed.add_field(name="Invite Code", value=f"{invite_code}", inline=False)
            created = int(member.created_at.timestamp())
            embed.add_field(
                name="Account Created",
                value=f"<t:{created}:D> \n<t:{created}:t> \n<t:{created}:R>",
                inline=True,
            )
            joined = int(member.joined_at.timestamp())
            embed.add_field(
                name="Joined",
                value=f"<t:{joined}:D> \n<t:{joined}:t> \n<t:{joined}:R>",
                inline=True,
            )
            if member.bot:
                embed.color = 0x2F3136
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed.color = discord.Color.blurple()
            # Add member to member hall and database
            member_hall: discord.TextChannel = discord.utils.get(
                member.guild.channels, name="member-hall"
            )
            message: discord.Message = await member_hall.send(embed=embed)
            message_id = message.id
            member_collection = self.bot.database["members"]
            member_collection.insert_one(
                {
                    "discord_id": member.id,
                    "message_id": message_id,
                    "channel_id": member_hall.id,
                    "joined_at": member.joined_at,
                    "invite_url": invite_code,
                    "is_bot": member.bot,
                }
            )
        await ctx.respond("Done!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Add a member to the member hall and database"""
        print(f"{member.display_name} joined the server.")
        self.logger.info("Member %s joined the server.", member.display_name)
        embed = discord.Embed(title=f"{member.display_name}")
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="User Info",
            value=f"<@{member.id}> \n**ID**: {member.id}",
            inline=False,
        )
        invite_code = await self.get_latest_invite_code(member=member)
        if not invite_code or invite_code == []:
            invite_code = "None"
        embed.add_field(name="Invite Code", value=f"{invite_code}", inline=False)
        created = int(member.created_at.timestamp())
        embed.add_field(
            name="Account Created",
            value=f"<t:{created}:D> \n<t:{created}:t> \n<t:{created}:R>",
            inline=True,
        )
        joined = int(member.joined_at.timestamp())
        embed.add_field(
            name="Joined",
            value=f"<t:{joined}:D> \n<t:{joined}:t> \n<t:{joined}:R>",
            inline=True,
        )
        if member.bot:
            embed.color = 0x2F3136
            embed.set_thumbnail(url=member.avatar.url)
        else:
            embed.color = discord.Color.blurple()
        # Add member to member hall and database
        member_hall: discord.TextChannel = discord.utils.get(
            member.guild.channels, name="member-hall"
        )

        # Prevent duplicate messages on join spam
        last_message = await member_hall.history(limit=1).flatten()
        if last_message[0].embeds:
            last_message_embed = last_message[0].embeds[0]
            if last_message_embed.title == embed.title:
                return
        message: discord.Message = await member_hall.send(embed=embed)
        message_id = message.id
        member_collection = self.bot.database["members"]
        member_collection.insert_one(
            {
                "discord_id": member.id,
                "message_id": message_id,
                "channel_id": member_hall.id,
                "joined_at": member.joined_at,
                "invite_url": invite_code,
                "is_bot": member.bot,
            }
        )

        # Give member the correct role
        if invite_code == self.bot.destiny_invite_code:
            role = discord.utils.get(member.guild.roles, name="Friendly Lights")
            if role:
                await member.add_roles(role)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Remove a member from the member hall and database"""
        print(f"{member.display_name} left the server.")
        self.logger.info("Member %s left the server.", member.display_name)
        member_collection = self.bot.database["members"]
        entries = member_collection.find({"discord_id": member.id})
        # Remove member to member hall and database
        member_hall = discord.utils.get(member.guild.channels, name="member-hall")
        for entry in entries:
            message_id = entry["message_id"]
            message = await member_hall.fetch_message(message_id)
            await message.delete()
        member_collection.delete_many({"discord_id": member.id})
        # Remove member from notify-shaders.csv
        with open("data/notify-shaders.csv", "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            ids = [int(row[0]) for row in reader]
        if member.id in ids:
            ids.remove(member.id)
        with open("data/notify-shaders.csv", "w", encoding="utf-8") as file:
            writer = csv.writer(file)
            for _id in ids:
                writer.writerow([_id])


def setup(bot) -> None:
    bot.add_cog(MemberManager(bot))
