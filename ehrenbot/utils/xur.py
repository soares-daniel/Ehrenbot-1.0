import datetime
import logging

import discord

from ehrenbot.bot import Ehrenbot
from ehrenbot.utils.utils_rotations import (armor_embed_field,
                                            create_emoji_from_entry,
                                            fetch_vendor_sales,
                                            weapon_embed_field)


async def xur_rotation(bot: Ehrenbot, logger: logging.Logger):
    channel: discord.TextChannel = discord.utils.get(bot.get_all_channels(), name="vendor-sales")
    if not channel:
        logger.error("Failed to find vendor-sales channel")
        return
    logger.info("Starting daily vendor rotation...")
    # Fetch vendor sales and send embeds
    rotation_collection = bot.database["destiny_rotation"]
    vendor_hash = 2190858386
    if not await fetch_vendor_sales(bot=bot, logger=logger, vendor_hash=vendor_hash):
        logger.error("Failed to fetch vendor sales for vendor %s", vendor_hash)
        return
    bot.vendor_guild_id = 1057711135668850688
    embed = await xur_embed(bot)
    # Set footer
    current_time = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text=f"Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    entry = rotation_collection.find_one({"vendor_hash": vendor_hash})
    if _id := entry.get("message_id"):
        message = await channel.fetch_message(_id)
        await message.edit(content="", embed=embed)
    else:
        await channel.send(content="", embed=embed)
        _id = channel.last_message_id
        rotation_collection.update_one({"vendor_hash": vendor_hash}, {"$set": {"message_id": _id}}, upsert=True)
    logger.debug("Sent embed for vendor %s", vendor_hash)

async def exotic_armor_embed_field(bot: Ehrenbot, vendor_hash: int) -> str:
    """Returns a string with all the exotic armor for a specific vendor and category"""
    daily_rotation = bot.database["destiny_rotation"].find_one({"vendor_hash": vendor_hash})
    intenvory_item_collection = bot.mongo_client["d2manifest_en"]["DestinyInventoryItemDefinition"]
    armor = daily_rotation["armor"]
    exotic_armor_string = ""
    for item in armor:
        if armor[item]["definition"]["inventory"]["tierType"] != 6:
            continue
        item_hash = armor[item]["item_hash"]
        item_name = armor[item]["definition"]["displayProperties"]["name"]
        emoji = await create_emoji_from_entry(bot=bot, logger=bot.logger, item_hash=item_hash,
                                              collection=intenvory_item_collection, vendor_hash=vendor_hash)
        exotic_armor_string += f"<:{emoji.name}:{emoji.id}> {item_name}\n"
    return exotic_armor_string

async def exotic_weapon_embed_field(bot: Ehrenbot, vendor_hash: int) -> str:
    """Returns a string with all the exotic weapons for a specific vendor and category"""
    daily_rotation = bot.database["destiny_rotation"].find_one({"vendor_hash": vendor_hash})
    intenvory_item_collection = bot.mongo_client["d2manifest_en"]["DestinyInventoryItemDefinition"]
    weapons = daily_rotation["weapons"]
    exotic_weapon_string = ""
    for item in weapons:
        if weapons[item]["definition"]["inventory"]["tierType"] != 6:
            continue
        item_hash = weapons[item]["item_hash"]
        item_name = weapons[item]["definition"]["displayProperties"]["name"]
        emoji = await create_emoji_from_entry(bot=bot, logger=bot.logger, item_hash=item_hash,
                                              collection=intenvory_item_collection, vendor_hash=vendor_hash)
        exotic_weapon_string += f"<:{emoji.name}:{emoji.id}> {item_name}\n"
    return exotic_weapon_string

async def xur_embed(bot: Ehrenbot) -> discord.Embed:
    xur = bot.database["destiny_rotation"].find_one({"vendor_hash": 2190858386})
    vendor_location_index = xur["vendor"]["vendorLocationIndex"]
    vendor_locations = {0: "The Last City, Tower", 1: "European Dead Zone, EDZ", 2: "Arcadian Valley, Nessus"}
    vendor_location = vendor_locations[vendor_location_index]
    embed = discord.Embed(title="Xûr",
                          description=f"Xûr is a vendor who sells exotic weapons, armor. \nCurrent location: **{vendor_location}**", color=0xcdad36)
    vendor_hash = 2190858386
    embed.set_thumbnail(url="https://www.light.gg/Content/Images/xur-icon.png")
    embed.set_image(url="https://www.bungie.net/common/destiny2_content/icons/801c07dc080b79c7da99ac4f59db1f66.jpg")
    exotics_weapon_string = await exotic_weapon_embed_field(bot=bot, vendor_hash=vendor_hash)
    embed.add_field(name="Exotic Weapons", value=exotics_weapon_string, inline=True)
    exotics_armor_string = await exotic_armor_embed_field(bot=bot, vendor_hash=vendor_hash)
    embed.add_field(name="Exotic Armor", value=exotics_armor_string, inline=True)
    weapons_string = await weapon_embed_field(bot=bot, vendor_hash=vendor_hash)
    embed.add_field(name='\u200b', value='\u200b', inline=False)
    embed.add_field(name="Weapons", value=weapons_string, inline=True)
    warlock_armor_string = await armor_embed_field(bot=bot, vendor_hash=vendor_hash, category="Warlock")
    embed.add_field(name="Warlock Armor", value=warlock_armor_string, inline=True)
    titan_armor_string = await armor_embed_field(bot=bot, vendor_hash=vendor_hash, category="Titan")
    embed.add_field(name='\u200b', value='\u200b', inline=False)
    embed.add_field(name="Titan Armor", value=titan_armor_string, inline=True)
    hunter_armor_string = await armor_embed_field(bot=bot, vendor_hash=vendor_hash, category="Hunter")
    embed.add_field(name="Hunter Armor", value=hunter_armor_string, inline=True)
    return embed
