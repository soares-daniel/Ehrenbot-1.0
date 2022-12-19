# pylint: disable=E0211,E1121,C0206,E1123
import logging
from datetime import date, time, timezone

from discord.ext import commands, tasks

from ehrenbot import Ehrenbot
from ehrenbot.utils.utils_rotations import loop_check, sort_sales, vendor_sales


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
        last_message_id = ctx.channel.last_message_id

        vendor_hash = 2190858386
        if not await vendor_sales(bot=self.bot, logger=self.logger, vendor_hash=vendor_hash):
            await ctx.respond("ERROR")
            return
        destiny_rotation = self.bot.database["destiny_rotation"]
        sorted_items = destiny_rotation.find_one({"vendor_hash": vendor_hash}).get("sorted_sales")
        if not sorted_items:
            await sort_sales(bot=self.bot, logger=self.logger, vendor_hash=vendor_hash)
        for category in sorted_items:
            display_items = []
            for item in sorted_items[category]:
                display_items.append(item["displayProperties"]["name"])
            message = await ctx.channel.fetch_message(last_message_id)
            content = message.content
            if content == "Checking for vendor data...":
                await message.edit(content=f"\u200b{category} {display_items}\u200b")
            else:
                await message.edit(content=f"\u200b{content}\n{category} {display_items}\u200b")

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
