# pylint: disable=E0211,E1121,C0206,E1123
import csv
import logging
from datetime import date, datetime, time, timezone

import discord
from discord.ext import commands, tasks

from ehrenbot import Ehrenbot
from ehrenbot.utils.utils_rotations import loop_check, vendor_rotation
from ehrenbot.utils.xur import xur_rotation


class Rotations(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)
        self.daily_vendor_rotation.start()
        self.delete_emojis_loop.start()

    def cog_unload(self) -> None:
        self.daily_vendor_rotation.cancel()

    def get_reset_time() -> time:
        return time(
            hour=18, minute=1, second=0, tzinfo=timezone.utc
        )  # 1 minute after reset to prevent downtime issues

    rotation = discord.SlashCommandGroup(
        name="rotation",
        description="Commands to start Destiny 2 vendor rotations manually.",
    )

    @rotation.command(name="banshee", description="Start Banshee-44 rotation manually.")
    async def rotation_banshee_ada(self, ctx: discord.ApplicationContext):
        """Start Banshee-44 rotation manually."""
        self.banshee.start()
        await ctx.respond("Banshee-44 rotation started.", delete_after=2)

    @rotation.command(name="ada", description="Start Ada-1 rotation manually.")
    async def rotation_ada(self, ctx: discord.ApplicationContext):
        """Start Ada-1 rotation manually."""
        self.ada.start()
        await ctx.respond("Ada-1 rotation started.", delete_after=2)

    @rotation.command(name="xur", description="Start Xur rotation manually.")
    async def rotation_xur(self, ctx: discord.ApplicationContext):
        """Start Xur rotation manually."""
        self.xur.start()
        await ctx.respond("Xur rotation started.", delete_after=2)

    @rotation.command(
        name="del_emojis",
        description="Deletes all emojis from a guild. ONLY USE ON ROTATION SERVERS!",
    )
    async def del_emojis(self, ctx: discord.ApplicationContext, guild_id: int = 0):
        await ctx.defer()
        if guild_id == 0:
            guild_id = ctx.guild.id
        guild = self.bot.get_guild(guild_id)
        for emoji in guild.emojis:
            await guild.delete_emoji(emoji)
        await ctx.respond(f"Deleted all emojis from guild {guild_id}", delete_after=5)

    @rotation.command(
        name="del_emoji_all", description="Deletes all emojis from all rotation servers"
    )
    async def del_emoji_all(self, ctx: discord.ApplicationContext):
        await self.delete_emojis.start()
        await ctx.respond(
            "Deleting emojis from all rotation servers...", delete_after=5
        )

    @rotation.command(
        name="activate_notifications_shader",
        description="Activates shader notifications",
    )
    async def activate_notifications_shader(self, ctx: discord.ApplicationContext):
        tokens = self.bot.database["destiny_tokens"]
        with open("data/notify-shaders.csv", "w", encoding="utf-8") as file:
            writer = csv.writer(file)
            for token in tokens.find():
                writer.writerow([token["discord_id"]])
        await ctx.respond("Shader notifications activated.", delete_after=5)

    @rotation.command(
        name="ada_shaders_to_database",
        description="Adds all ada shaders to the database",
    )
    async def shaders_to_database(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        # Get full Ada-1 item list
        vendor_collection = await self.bot.destiny_client.decode_hash(
            350061650, "DestinyVendorDefinition"
        )
        vendor_items = vendor_collection["itemList"]
        vendor_items = [
            await self.bot.destiny_client.decode_hash(
                item["itemHash"], "DestinyInventoryItemDefinition"
            )
            for item in vendor_items
        ]

        # Filter out non-shaders
        shaders = [item for item in vendor_items if 41 in item["itemCategoryHashes"]]

        shader = {
            "hash": 0,
            "name": "",
            "icon": "",
            "definition": {},
        }

        collection = self.bot.database["destiny_shaders"]
        for item in shaders:
            existing_shader = collection.find_one({"hash": item["hash"]})
            if existing_shader:
                continue
            new_shader = (
                shader.copy()
            )  # Create a new copy of the template for each shader
            new_shader["hash"] = item["hash"]
            new_shader["name"] = item["displayProperties"]["name"]
            new_shader["icon"] = item["displayProperties"]["icon"]
            new_shader["definition"] = item
            collection.insert_one(new_shader)

        await ctx.respond("Added all shaders to database.", delete_after=5)

    @tasks.loop(time=get_reset_time())
    async def daily_vendor_rotation(self):
        self.banshee.start()
        self.ada.start()
        self.xur.start()

    @daily_vendor_rotation.before_loop
    async def before_daily_vendor_rotation(self):
        await self.bot.wait_until_ready()
        if not await loop_check(self.bot):
            self.daily_vendor_rotation.cancel()

    @tasks.loop(time=time(hour=1, minute=0, second=0, tzinfo=timezone.utc))
    async def delete_emojis_loop(self):
        await self.delete_emojis.start()

    @delete_emojis_loop.before_loop
    async def before_delete_emojis_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(count=1)
    async def ada(self):
        await vendor_rotation(self.bot, self.logger, 350061650)

    @tasks.loop(count=1)
    async def banshee(self):
        await vendor_rotation(self.bot, self.logger, 672118013)

    @tasks.loop(count=1)
    async def xur(self):
        self.logger.debug("Starting Xur rotation...")
        weekdays = [1, 2, 3]
        if date.today().weekday() in weekdays:
            embed = discord.Embed(
                title="Xûr",
                description="Xur is not here today. He will return again on **Friday.**",
                color=0xCDAD36,
            )
            embed.set_thumbnail(url="https://www.light.gg/Content/Images/xur-icon.png")
            embed.set_image(
                url="https://www.bungie.net/common/destiny2_content/icons/801c07dc080b79c7da99ac4f59db1f66.jpg"
            )
            current_time = datetime.now(timezone.utc)
            embed.set_footer(
                text=f"Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            # Send embed to vendor channel
            rotation_collection = self.bot.database["destiny_rotation"]
            entry = rotation_collection.find_one({"vendor_hash": 2190858386})
            if entry is None:
                rotation_collection.insert_one(
                    {"vendor_hash": 2190858386, "message_id": 0}
                )
            entry = rotation_collection.find_one({"vendor_hash": 2190858386})
            if entry["message_id"] == 0:
                channel = discord.utils.get(
                    self.bot.get_all_channels(), name="vendor-sales"
                )
                message = await channel.send(content="", embed=embed)
                rotation_collection.update_one(
                    {"vendor_hash": 2190858386}, {"$set": {"message_id": message.id}}
                )
            else:
                message_id = entry["message_id"]
                channel = discord.utils.get(
                    self.bot.get_all_channels(), name="vendor-sales"
                )
                message = await channel.fetch_message(message_id)
                await message.edit(content="", embed=embed)
        else:  # Xur is here
            await xur_rotation(self.bot, self.logger)

    @tasks.loop(count=1)
    async def delete_emojis(self):
        xur_guid_id = 1057711135668850688
        banshee_guild_id = 1057709724843397282
        ada_guild_id = 1057710325631295590
        guilds = [xur_guid_id, banshee_guild_id, ada_guild_id]
        for guild_id in guilds:
            guild = self.bot.get_guild(guild_id)
            for emoji in guild.emojis:
                await guild.delete_emoji(emoji)


def setup(bot) -> None:
    bot.add_cog(Rotations(bot))
