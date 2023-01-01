# pylint: disable=E0211,E1121,C0206,E1123
import logging
from datetime import date, datetime, time, timezone

import discord
from discord.ext import commands, tasks

from ehrenbot import Ehrenbot
from ehrenbot.utils.utils_rotations import banshee_ada_rotation, loop_check


class Rotations(commands.Cog):
    def __init__(self, bot):
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)
        self.daily_vendor_rotation.start()
        self.xur_rotation.start()

    def cog_unload(self) -> None:
        self.daily_vendor_rotation.cancel()
        self.xur_rotation.cancel()

    def get_reset_time() -> time:
        return time(hour=17, minute=0, second=0, tzinfo=timezone.utc)

    rotation = discord.SlashCommandGroup(name="rotation", description="Commands to start Destiny 2 vendor rotations manually.")

    @rotation.command(name="banshee_ada", description="Start Banshee-44 and Ada-1 rotation manually.")
    async def rotation_banshee_ada(self, ctx: discord.ApplicationContext):
        """ Start Banshee-44 and Ada-1 rotation manually. """
        await banshee_ada_rotation(self.bot, self.logger)
        await ctx.respond("Banshee-44 and Ada-1 rotation started.", ephemeral=True, delete_after=5)

    @rotation.command(name="del_emojis", description="Deletes all emojis from a guild. ONLY USE ON ROTATION SERVERS!")
    async def del_emojis(self, ctx: discord.ApplicationContext, guild_id: int = 0):
        await ctx.defer()
        if guild_id == 0:
            guild_id = ctx.guild.id
        guild = self.bot.get_guild(guild_id)
        for emoji in guild.emojis:
            await guild.delete_emoji(emoji)
        await ctx.respond(f"Deleted all emojis from guild {guild_id}")

    # ! if already in database, retry again in 5 minutes
    @tasks.loop(hours=1)
    async def daily_vendor_rotation(self):
        await banshee_ada_rotation(self.bot, self.logger)
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

    @daily_vendor_rotation.before_loop
    async def before_daily_vendor_rotation(self):
        await self.bot.wait_until_ready()
        if not await loop_check(self.bot):
            self.daily_vendor_rotation.cancel()

    @tasks.loop(hours=1)
    async def xur_rotation(self):
        self.logger.debug("Starting Xur rotation...")
        weekdays = [0, 1, 2, 3]
        if date.today().weekday() in weekdays:
            embed = discord.Embed(title="Xûr", description="Xur is not here today. He will return again on **Friday.**", color=0xcdad36)
        elif date.today().weekday() == 4:
            embed = discord.Embed(title="Xûr", description="XUR ROTATION IS NOT IMPLEMENTED YET", color=0xcdad36)
        else:
            embed = discord.Embed(title="Xûr", description="XUR ROTATION IS NOT IMPLEMENTED YET", color=0xcdad36)
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

    @xur_rotation.before_loop
    async def before_xur_rotation(self):
        await self.bot.wait_until_ready()
        if not await loop_check(self.bot):
            self.xur_rotation.cancel()

def setup(bot) -> None:
    bot.add_cog(Rotations(bot))
