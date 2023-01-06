# pylint: disable=E0211,E1121,C0206,E1123
import asyncio
import logging
from datetime import date, datetime, time, timezone

import discord
from discord.ext import commands, tasks

from ehrenbot import Ehrenbot
from ehrenbot.utils.utils_rotations import banshee_ada_rotation, loop_check
from ehrenbot.utils.xur import xur_rotation


class Rotations(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)
        self.daily_vendor_rotation.start()

    def cog_unload(self) -> None:
        self.daily_vendor_rotation.cancel()

    def get_reset_time() -> time:
        return time(hour=17, minute=0, second=0, tzinfo=timezone.utc)

    rotation = discord.SlashCommandGroup(name="rotation", description="Commands to start Destiny 2 vendor rotations manually.")

    @rotation.command(name="banshee_ada", description="Start Banshee-44 and Ada-1 rotation manually.")
    async def rotation_banshee_ada(self, ctx: discord.ApplicationContext):
        """ Start Banshee-44 and Ada-1 rotation manually. """
        self.banshee_ada.start()
        await ctx.respond("Banshee-44 and Ada-1 rotation started.", delete_after=5)

    @rotation.command(name="xur", description="Start Xur rotation manually.")
    async def rotation_xur(self, ctx: discord.ApplicationContext):
        """ Start Xur rotation manually. """
        self.xur.start()
        await ctx.respond("Xur rotation started.", delete_after=5)

    @rotation.command(name="del_emojis", description="Deletes all emojis from a guild. ONLY USE ON ROTATION SERVERS!")
    async def del_emojis(self, ctx: discord.ApplicationContext, guild_id: int = 0):
        await ctx.defer()
        if guild_id == 0:
            guild_id = ctx.guild.id
        guild = self.bot.get_guild(guild_id)
        for emoji in guild.emojis:
            await guild.delete_emoji(emoji)
        await ctx.respond(f"Deleted all emojis from guild {guild_id}", delete_after=5)

    @tasks.loop(time=get_reset_time())
    async def daily_vendor_rotation(self):
        self.banshee_ada.start()
        self.xur.start()

    @daily_vendor_rotation.before_loop
    async def before_daily_vendor_rotation(self):
        await self.bot.wait_until_ready()
        if not await loop_check(self.bot):
            self.daily_vendor_rotation.cancel()

    @tasks.loop(count=1)
    async def banshee_ada(self):
        await banshee_ada_rotation(self.bot, self.logger)

        await asyncio.sleep(3600)
        # Delete previous emojis
        emoji_collection = self.bot.database["emojis"]
        for entry in emoji_collection.find({"vendor_hash": {"$in": [672118013, 350061650]}}):
            emoji_id = entry["emoji_id"]
            guild_id = entry["guild_id"]
            emoji =  await self.bot.get_guild(guild_id).fetch_emoji(emoji_id)
            await self.bot.get_guild(guild_id).delete_emoji(emoji)
            emoji_collection.delete_one({"emoji_id": emoji_id})
            self.logger.debug("Deleted emoji %s from guild %s", emoji.name, guild_id)
        self.logger.debug("Done deleting emojis")

    @tasks.loop(count=1)
    async def xur(self):
        self.logger.debug("Starting Xur rotation...")
        weekdays = [1, 2, 3]
        if date.today().weekday() in weekdays:
            embed = discord.Embed(title="Xûr", description="Xur is not here today. He will return again on **Friday.**", color=0xcdad36)
            embed.set_thumbnail(url="https://www.light.gg/Content/Images/xur-icon.png")
            embed.set_image(url="https://www.bungie.net/common/destiny2_content/icons/801c07dc080b79c7da99ac4f59db1f66.jpg")
            current_time = datetime.now(timezone.utc)
            embed.set_footer(text=f"Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

            # Send embed to vendor channel
            rotation_collection = self.bot.database["destiny_rotation"]
            entry = rotation_collection.find_one({"vendor_hash": 2190858386})
            if entry is None:
                rotation_collection.insert_one({"vendor_hash": 2190858386, "message_id": 0})
            entry = rotation_collection.find_one({"vendor_hash": 2190858386})
            if entry["message_id"] == 0:
                channel = discord.utils.get(self.bot.get_all_channels(), name="vendor-sales")
                message = await channel.send(content="", embed=embed)
                rotation_collection.update_one({"vendor_hash": 2190858386}, {"$set": {"message_id": message.id}})
            else:
                message_id = entry["message_id"]
                channel = discord.utils.get(self.bot.get_all_channels(), name="vendor-sales")
                message = await channel.fetch_message(message_id)
                await message.edit(content="", embed=embed)

        elif date.today().weekday() == 4:
            await xur_rotation(self.bot, self.logger)
        else:
            return

        await asyncio.sleep(3600)
        # Delete previous emojis
        emoji_collection = self.bot.database["emojis"]
        for entry in emoji_collection.find({"vendor_hash": {"$in": [2190858386]}}):
            emoji_id = entry["emoji_id"]
            guild_id = entry["guild_id"]
            emoji =  await self.bot.get_guild(guild_id).fetch_emoji(emoji_id)
            await self.bot.get_guild(guild_id).delete_emoji(emoji)
            emoji_collection.delete_one({"emoji_id": emoji_id})
            self.logger.debug("Deleted emoji %s from guild %s", emoji.name, guild_id)
        self.logger.debug("Done deleting emojis")

def setup(bot) -> None:
    bot.add_cog(Rotations(bot))
