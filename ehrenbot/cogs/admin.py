import logging

import discord
from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

    @commands.slash_command(name="color", description="Change the color of a role.")
    @commands.has_role('Ehrenmänner und Ender')
    async def change_color(self, ctx, role: discord.Role, color: discord.Color):
        """ Change the color of a role """
        await role.edit(color=color)
        await ctx.respond(f"{role.name} has been changed to {color}")

    @commands.slash_command(name="nickname", description="Change the nickname of a member.")
    @commands.has_role('Ehrenmänner und Ender')
    async def change_nickname(self, ctx, member: discord.Member, nickname: str):
        """ Change the nickname of a member """
        await member.edit(nick=nickname)
        await ctx.respond(f"{member.name} has been changed to {nickname}")

def setup(bot) -> None:
    bot.add_cog(Admin(bot))
