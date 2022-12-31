# pylint: disable=E0211,E1121,C0206,E1123
import logging
from datetime import date, time, timezone, datetime

import aiohttp
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

    @commands.slash_command(name="test", description="Test command")
    async def del_emojis(self, ctx: discord.ApplicationContext, guild_id: int = 0):
        await ctx.defer()
        if guild_id == 0:
            guild_id = ctx.guild.id
        guild = self.bot.get_guild(guild_id)
        for emoji in guild.emojis:
            await guild.delete_emoji(emoji)
        await ctx.respond(f"Deleted all emojis from guild {guild_id}")

    @commands.slash_command(name="emoji", description="Get Xur's inventory")
    async def test_emoji(self, ctx: discord.ApplicationContext):
        manifest = self.bot.mongo_client["d2manifest_en"]
        destiny_stat_definition = manifest["DestinyStatDefinition"]
        stat_hash = 392767087
        stat = destiny_stat_definition.find_one({"hash": stat_hash})
        icon_url=stat["displayProperties"]["icon"]
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.bungie.net" + icon_url) as resp:
                emoji_img = await resp.read()
        emoji = await ctx.guild.create_custom_emoji(name="test", image=emoji_img)
        await ctx.respond(emoji)
        await ctx.guild.delete_emoji(emoji)

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

    @daily_vendor_rotation.before_loop
    async def before_daily_vendor_rotation(self):
        if not await loop_check(self.bot):
            self.daily_vendor_rotation.cancel()

    @tasks.loop(hours=1)
    async def xur_rotation(self):
        self.logger.debug("Updating Xur's inventory")
        weekdays = [0, 1, 2, 3]
        if date.today().weekday() in weekdays:
            embed = discord.Embed(title="Xur's inventory", description="Xur is not here today. He will return again on **Friday.**")
        elif date.today().weekday() == 4:
            embed = discord.Embed(title="Xur's inventory", description="XUR ROTATION IS NOT IMPLEMENTED YET")
        else:
            embed = discord.Embed(title="Xur's inventory", description="XUR ROTATION IS NOT IMPLEMENTED YET")
        embed.set_image(url="https://i.imgur.com/4ZQZ9Zm.png")
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
            message = await channel.send(embed=embed)
            rotation_collection.update_one({"vendor_hash": 2190858386}, {"$set": {"message_id": message.id}})
        else:
            message_id = entry["message_id"]
            channel = discord.utils.get(self.bot.get_all_channels(), name="vendor-sales")
            message = await channel.fetch_message(message_id)
            await message.edit(embed=embed)

    @xur_rotation.before_loop
    async def before_xur_rotation(self):
        if not await loop_check(self.bot):
            self.xur_rotation.cancel()

def setup(bot) -> None:
    bot.add_cog(Rotations(bot))
