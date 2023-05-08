import logging
import os

import discord
from discord.ext import commands

from ehrenbot.bot import Ehrenbot
from ehrenbot.utils.registration import setup_profile, update_profile


class Owner(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

    owner = discord.SlashCommandGroup(name="owner", description="Owner commands.")

    def get_cogs(self) -> list:
        return [
            cog.replace(".py", "")
            for cog in os.listdir("ehrenbot/cogs")
            if cog.endswith(".py") and not cog.startswith("_")
        ]

    @owner.command(name="reload", description="Reload a cog.")
    @commands.is_owner()
    async def reload(self, ctx, cog: discord.Option(str, autocomplete=get_cogs)):
        """Reload a cog"""
        self.bot.reload_extension(f"ehrenbot.cogs.{cog}")
        await ctx.respond(f"Reloaded {cog}", delete_after=5)

    @owner.command(name="load", description="Load a cog.")
    @commands.is_owner()
    async def load(self, ctx, cog: discord.Option(str, autocomplete=get_cogs)):
        """Load a cog"""
        self.bot.load_extension(f"ehrenbot.cogs.{cog}")
        await ctx.respond(f"Loaded {cog}", delete_after=5)

    @owner.command(name="unload", description="Unload a cog.")
    @commands.is_owner()
    async def unload(self, ctx, cog: discord.Option(str, autocomplete=get_cogs)):
        """Unload a cog"""
        self.bot.unload_extension(f"ehrenbot.cogs.{cog}")
        await ctx.respond(f"Unloaded {cog}", delete_after=5)

    @owner.command(
        name="migrate_destiny_profile",
        description="Migrate destiny profile to members collection",
    )
    @commands.is_owner()
    async def migrate_destiny_profile(self, ctx: discord.ApplicationContext):
        """Migrate destiny profile to members collection"""
        await ctx.defer()
        profiles_collection = self.bot.database["destiny_profiles"]
        members_collection = self.bot.database["members"]
        for entry in profiles_collection.find():
            discord_id = entry["discord_id"]
            destiny_profile = entry["profile"]
            membership_id = entry["membershipId"]
            members_collection.update_one(
                {"discord_id": discord_id},
                {
                    "$set": {
                        "destiny_profile": destiny_profile,
                        "membership_id": membership_id,
                    }
                },
            )
        await ctx.respond(
            "Migrated destiny profile to members collection", delete_after=5
        )

    @owner.command(
        name="update_memberhall",
        description="Migrate destiny profile to members collection",
    )
    @commands.is_owner()
    async def update_member_destiny(self, ctx: discord.ApplicationContext):
        """Update member hall"""
        await ctx.defer()
        members_collection = self.bot.database["members"]
        for entry in members_collection.find():
            if "destiny_profile" in entry:
                message_id = entry["message_id"]
                channel: discord.TextChannel = ctx.guild.get_channel(
                    entry["channel_id"]
                )
                message = await channel.fetch_message(message_id)
                embed = message.embeds[0]
                name = entry["destiny_profile"]["unique_name"]
                embed.add_field(name="Bungie.Net", value=f"\u200b{name}", inline=False)
                embed.color = discord.Color.green()
                await message.edit(content="", embed=embed)
        await ctx.respond("Updated member hall", delete_after=5)

    @owner.command(name="update_profile_man", description="Update profile manually")
    @commands.is_owner()
    async def update_profile_manually(
        self, ctx: discord.ApplicationContext, discord_id=None
    ):
        """Update profile"""
        await ctx.defer()
        if discord_id is None:
            members_collection = self.bot.database["members"]
            token_collection = self.bot.database["destiny_tokens"]
            for token in token_collection.find():
                entry = members_collection.find_one({"discord_id": token["discord_id"]})
                if entry:
                    await setup_profile(
                        self.bot, token["discord_id"], token["membership_id"]
                    )
                    await update_profile(self.bot, entry["discord_id"])
        else:
            discord_id = int(discord_id)
            members_collection = self.bot.database["members"]
            token_collection = self.bot.database["destiny_tokens"]
            token = token_collection.find_one({"discord_id": discord_id})
            entry = members_collection.find_one({"discord_id": discord_id})
            if entry:
                await setup_profile(
                    self.bot, token["discord_id"], token["token"]["membership_id"]
                )
                await update_profile(self.bot, entry["discord_id"])
            else:
                await ctx.respond("No profile found", delete_after=5)
                return
        await ctx.respond("Updated profile/s", delete_after=5)


def setup(bot) -> None:
    bot.add_cog(Owner(bot))
