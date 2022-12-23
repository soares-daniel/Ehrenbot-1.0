# pylint: disable=E0211,E1121,C0206,E1123
import datetime
import logging
from datetime import date, time, timezone

import aiohttp
import discord
from discord.ext import commands, tasks

from ehrenbot import Ehrenbot
from ehrenbot.utils.utils_rotations import (fetch_vendor_sales, get_missing_mods, loop_check,
                                            sort_sales, vendor_embed,
                                            xur_embed)


class Rotations(commands.Cog):
    def __init__(self, bot):
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)
        self.daily_rotation.start()

    def get_reset_time() -> time:
        return time(hour=17, minute=0, second=0, tzinfo=timezone.utc)


    @commands.slash_command(name="vendor_test", description="Test vendor command")
    async def vendor_test(self, ctx: commands.Context):
        await ctx.respond("Checking for vendor data...")

        vendor_hash = 2190858386
        if not await fetch_vendor_sales(bot=self.bot, logger=self.logger, vendor_hash=vendor_hash):
            await ctx.send("ERROR")
            return
        await ctx.send("SUCCESS")

    @commands.slash_command(name="embed_test", description="Test embed command")
    async def embed_test(self, ctx: commands.Context):
        await ctx.respond("Checking for vendor data...")
        embed = await xur_embed(bot=self.bot)
        await ctx.send(embed=embed)

    @commands.slash_command(name="emoji", description="Get Xur's inventory")
    async def test_emoji(self, ctx: commands.Context):
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

    @tasks.loop(hours=1)
    async def daily_rotation(self):
        channel: discord.TextChannel = discord.utils.get(self.bot.get_all_channels(), name="vendor-sales")
        if not channel:
            self.logger.error("Failed to find vendor-sales channel")
            return
        self.logger.info("Starting daily rotation...")

        # Delete previous emojis
        emoji_collection = self.bot.database["emojis"]
        for entry in emoji_collection.find():
            emoji_id = entry["emoji"]
            guild_id = entry["guild_id"]
            emoji =  await self.bot.get_guild(guild_id).fetch_emoji(emoji_id)
            await self.bot.get_guild(guild_id).delete_emoji(emoji)
            emoji_collection.delete_one({"_id": emoji["_id"]})
            self.logger.debug("Deleted emoji %s from guild %s", emoji.name, guild_id)

        # Fetch vendor sales and send embeds
        rotation_collection = self.bot.database["destiny_rotation"]
        vendor_hashes = [672118013, 350061650]
        for vendor_hash in vendor_hashes:
            if not await fetch_vendor_sales(bot=self.bot, logger=self.logger, vendor_hash=vendor_hash):
                self.logger.error("Failed to fetch vendor sales for vendor %s", vendor_hash)
                return
            embed = await vendor_embed(bot=self.bot, vendor_hash=vendor_hash)
            entry = rotation_collection.find_one({"vendor_hash": vendor_hash})
            if _id := entry.get("message_id"):
                message = await channel.fetch_message(_id)
                await message.edit(content="", embed=embed)
            else:
                await channel.send(content="", embed=embed)
                _id = channel.last_message_id
                rotation_collection.update_one({"vendor_hash": vendor_hash}, {"$set": {"message_id": _id}}, upsert=True)
            self.logger.debug("Sent embed for vendor %s", vendor_hash)

        # Notify members for mods
        self.logger.debug("Notifying members for missing mods...")
        with open("data/notify-mods.csv", "r") as f:
            notify_mods = f.read().splitlines()
        for member_id in notify_mods:
            member = await self.bot.fetch_user(member_id)
            missing_mods = await get_missing_mods(bot=self.bot, logger=self.logger, discord_id=int(member_id))
            if missing_mods == {"message": "You have all mods!"}:
                notify_mods.remove(member_id)
                await member.send("You have all mods! You will no longer be notified.")
            if missing_mods == {672118013: [], 350061650: []} or missing_mods == {"message": "You have all mods!"}:
                continue
            member = await self.bot.fetch_user(member_id)
            ada_mods: list = missing_mods.get(350061650)
            banshee_mods: list = missing_mods.get(672118013)
            reset_time = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1)
            await member.send(f"You are missing mods from vendors! Go pick them up before it's too late!\nReset: {reset_time.strftime('%Y-%m-%d')} 17:00:00 UTC")
            if ada_mods:
                await member.send(f"Missing mods from Ada-1: ")
            if banshee_mods:
                await member.send(f"Missing mods from Banshee-44: {banshee_mods}")
            self.logger.debug("Sent notification to %s", member_id)
        # Update notify-mods.csv
        with open("data/notify-mods.csv", "w") as f:
            f.write("\n".join(notify_mods))
        self.logger.info("Daily rotation complete!")

    @daily_rotation.before_loop
    async def before_daily_rotation(self):
        if not await loop_check(self.bot):
            self.daily_rotation.cancel()

    @tasks.loop(time=get_reset_time())
    async def banshee_rotation(self):
        pass

    @banshee_rotation.before_loop
    async def before_banshee_rotation(self):
        if not await loop_check(self.bot):
            self.banshee_rotation.cancel()

    @tasks.loop(time=get_reset_time())
    async def ada_rotation(self):
        pass

    @ada_rotation.before_loop
    async def before_ada_rotation(self):
        if not await loop_check(self.bot):
            self.ada_rotation.cancel()

    @tasks.loop(time=get_reset_time())
    async def weekly_rotation(self):
        if not date.today().weekday() == 1:
            return

    @weekly_rotation.before_loop
    async def before_weekly_rotation(self):
        if not await loop_check(self.bot):
            self.weekly_rotation.cancel()

    @tasks.loop(time=get_reset_time())
    async def tess_rotation(self):
        if not date.today().weekday() == 1:
            return

    @tess_rotation.before_loop
    async def before_tess_rotation(self):
        if not await loop_check(self.bot):
            self.tess_rotation.cancel()

    @tasks.loop(time=get_reset_time())
    async def xur_rotation(self):
        if not date.today().weekday() == 4:
            return

    @xur_rotation.before_loop
    async def before_xur_rotation(self):
        if not await loop_check(self.bot):
            self.xur_rotation.cancel()

def setup(bot):
    bot.add_cog(Rotations(bot))
