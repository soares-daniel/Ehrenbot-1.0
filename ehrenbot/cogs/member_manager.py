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

    def find_invite_by_code(self, inv_list: list[discord.Invite], code: str) -> discord.Invite:
        """ Find an invite by its code """
        for invite in inv_list:
            if invite.code == code:
                return invite

    async def get_latest_invite_code(self, member: discord.Member) -> str:
        """ Get the invite code of the latest invite used by a member """
        invites_before = self.invites[member.guild.id]
        invites_after = await member.guild.invites()
        self.invites[member.guild.id] = invites_after
        for invite in invites_before:
            if invite.uses < self.find_invite_by_code(invites_after, invite.code).uses:
                return invite.code

    @commands.slash_command(name="invite", description="Get the invite link for the server.")
    async def invite(self, ctx: discord.ApplicationContext):
        await ctx.respond("test")
        for member in ctx.guild.members:
            embed = discord.Embed(title=f"{member.display_name}")
            embed.set_thumbnail(url=member.display_avatar.url)
            join_date = member.joined_at
            embed = embed.add_field(name="Joined", value=f"{join_date.strftime('%d.%m.%Y %H:%M')}")
            invite_code = await self.get_latest_invite_code(member=member)
            if not invite_code or invite_code == []:
                invite_code = "None"
            embed = embed.add_field(name="Invite Code", value=f"{invite_code}", inline=False)
            if member.bot:
                embed.color = 0x2f3136
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed.color = discord.Color.blurple()
            # Add member to member hall and database
            member_hall = discord.utils.get(member.guild.channels, name="member-hall")
            message: discord.Message = await member_hall.send(embed=embed)
            message_id = message.id
            member_collection = self.bot.database["members"]
            member_collection.insert_one({"discord_id": member.id, "message_id": message_id,
                                        "joined_at": member.joined_at, "invite_url": invite_code})

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """ Add a member to the member hall and database """
        self.logger.info("Member %s joined the server.", member.display_name)
        embed = discord.Embed(title=f"{member.display_name}")
        embed.set_thumbnail(url=member.display_avatar.url)
        embed = embed.add_field(name="Joined the server", value=f"{member.joined_at}")
        invite_code = await self.get_latest_invite_code(member=member)
        embed = embed.add_field(name="Invite Code", value=f"{invite_code}")
        if member.bot:
            embed.color = 0x2f3136
            embed.set_thumbnail(url=member.avatar.url)
        else:
            embed.color = discord.Color.blurple()
        # Add member to member hall and database
        member_hall: discord.TextChannel = discord.utils.get(member.guild.channels, name="member-hall")

        # Prevent duplicate messages on join spam
        last_message = await member_hall.history(limit=1).flatten()
        last_message_embed = last_message[0].embeds[0]
        if last_message_embed.title == embed.title:
            return
        
        message: discord.Message = await member_hall.send(embed=embed)
        message_id = message.id
        member_collection = self.bot.database["members"]
        member_collection.insert_one({"discord_id": member.id, "message_id": message_id,
                                      "joined_at": member.joined_at, "invite_url": invite_code})

        # Give member the correct role
        if invite_code == self.bot.destiny_invite_code:
            role = discord.utils.get(member.guild.roles, name="Friendly Lights")
            if role:
                await member.add_roles(role)
        if invite_code == self.bot.lux_invite_code:
            role = discord.utils.get(member.guild.roles, name="Luxembourg's Finest")
            if role:
                await member.add_roles(role)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """ Remove a member from the member hall and database """
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


def setup(bot) -> None:
    bot.add_cog(MemberManager(bot))
