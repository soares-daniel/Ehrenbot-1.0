# pylint: disable=E0211,E1121,C0206,E1123
import aiohttp
import logging
from datetime import date, time, timezone

from discord.ext import commands, tasks

from ehrenbot import Ehrenbot
from ehrenbot.utils.utils_rotations import loop_check, sort_sales, fetch_vendor_sales, xur_embed


class Rotations(commands.Cog):
    def __init__(self, bot):
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

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

    @tasks.loop(time=get_reset_time())
    async def daily_rotation(self):
        pass

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
