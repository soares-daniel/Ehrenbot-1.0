import logging

import discord
from discord.ext import commands

from ehrenbot.bot import Ehrenbot


class Luxembourg(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

    @commands.user_command(name="Luxembourg's Finest")
    @commands.has_role(955138929160515624)
    async def lux_role(self, ctx: discord.ApplicationContext, member: discord.Member):
        try:
            role = ctx.guild.get_role(955138929160515624)
            if member in role.members:
                await member.remove_roles(role)
                await ctx.respond(f"Removed {role.name} from {member.name}", ephemeral=True, delete_after=5)
            else:
                await member.add_roles(role)
                await ctx.respond(f"Added {role.name} to {member.name}", ephemeral=True, delete_after=5)
        except Exception as ex:
            self.logger.error(ex)
            await ctx.respond("Something went wrong", ephemeral=True, delete_after=5)

def setup(bot) -> None:
    bot.add_cog(Luxembourg(bot))
