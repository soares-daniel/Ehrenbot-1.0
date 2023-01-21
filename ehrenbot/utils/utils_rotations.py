import asyncio
import datetime
import json
from datetime import timezone
from logging import Logger
from typing import Union

import aiohttp
import discord
from pymongo.collection import Collection

from ehrenbot import Ehrenbot
from ehrenbot.utils.exceptions import (BungieMaintenance,
                                       DestinyVendorNotFound, NoBungieResponse)


async def check_vendors(bot: Ehrenbot) -> str:
    discord_id = bot.ADMIN_DISCORD_ID
    token_collection = bot.database["destiny_tokens"]
    profile_collection = bot.database["members"]
    token = token_collection.find_one({"discord_id": discord_id})["token"]
    profile = profile_collection.find_one({"discord_id": discord_id})["destiny_profile"]
    destiny2 = bot.destiny_client.destiny2
    response = await destiny2.GetVendors(token=token,
                                        character_id=profile["character_ids"][0],
                                        destiny_membership_id=profile["destiny_membership_id"],
                                        membership_type=profile["membership_type"],
                                        components=[400])
    if not response:
        return "No response from Bungie API"
    if response["ErrorCode"] == 1:
        return "OK"
    if response["ErrorCode"] == 5:
        return "Maintenance"

async def loop_check(bot: Ehrenbot) -> bool:
    """True if OK, False if no reponse.
    When in maintenance mode, it will retry every 5 minutes until it gets a response."""
    status = await check_vendors(bot)
    if status == "No response from Bungie API":
        user = bot.get_user(bot.ADMIN_DISCORD_ID)
        await user.send("No response from Bungie API for daily rotation")
        return False
    if status == "Maintenance":
        while status == "Maintenance":
            bot.logger.warning("Bungie API is in maintenance mode, retrying in 5 minutes")
            await asyncio.sleep(300)
            status = await check_vendors(bot)
    return True

async def get_vendor_data(bot: Ehrenbot, vendor_hash: int) -> dict:
    discord_id = bot.ADMIN_DISCORD_ID
    token_collection = bot.database["destiny_tokens"]
    profile_collection = bot.database["members"]
    token = token_collection.find_one({"discord_id": discord_id})["token"]
    profile = profile_collection.find_one({"discord_id": discord_id})["destiny_profile"]
    destiny2 = bot.destiny_client.destiny2
    result = {}
    for character_id in profile["character_ids"]:
        response = await destiny2.GetVendor(token=token,
                                            character_id=character_id,
                                            destiny_membership_id=profile["destiny_membership_id"],
                                            membership_type=profile["membership_type"],
                                            vendor_hash=vendor_hash,
                                            components=[400,402,304,305])
        if not response:
            raise NoBungieResponse
        if response["ErrorCode"] == 5:
            raise BungieMaintenance
        if response["ErrorCode"] == 1627:
            raise DestinyVendorNotFound
        result[character_id] = response["Response"]
    return result

async def fetch_vendor_sales(bot: Ehrenbot, logger: Logger, vendor_hash: int) -> bool:
    try:
        current_date = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d")
        destiny_rotation = bot.database["destiny_rotation"]
        if entry := destiny_rotation.find_one({"vendor_hash": vendor_hash}):
            date_str = entry.get("date")
            if date_str == current_date:
                logger.info("Vendor rotation already in database")
                return True
        destiny_rotation.update_one({"vendor_hash": vendor_hash}, {"$set": {"armor": [], "weapons": []}}, upsert=True)
        data = await get_vendor_data(bot=bot, vendor_hash=vendor_hash)

        modified_data = {"vendor": {}, "sales": {}, "stats": {}, "sockets": {}}
        for character_id in data:
            sales = data[character_id]["sales"]["data"]
            stats = data[character_id]["itemComponents"]["stats"]["data"]
            sockets = data[character_id]["itemComponents"]["sockets"]["data"]
            modified_data["sales"].update(sales)
            modified_data["stats"].update(stats)
            modified_data["sockets"].update(sockets)
        modified_data["vendor"] = data[list(data.keys())[0]]["vendor"]
    except NoBungieResponse:
        logger.error("No response from Bungie API")
        return False
    except BungieMaintenance:
        logger.error("Bungie API is in maintenance mode")
        return False
    except DestinyVendorNotFound:
        logger.warning("Vendor %d not found", vendor_hash)
        return False
    except Exception as ex:
        logger.error("Error: %s", ex)
        return False
    else:
        logger.debug("%d sales modified, processing...", vendor_hash)
        return await process_vendor_sales(bot=bot, logger=logger, vendor_hash=vendor_hash, data=modified_data)

async def process_vendor_sales(bot: Ehrenbot, logger: Logger, vendor_hash: int, data: dict) -> bool:
    try:
        armor = {}
        weapons = {}
        mods = {}
        sales_data = data["sales"]
        stats_data = data["stats"]
        sockets_data = data["sockets"]
        for item in sales_data:
            templates = {}
            with open("data/vendor_sale_item.json", "r", encoding="utf-8") as file:
                templates = json.load(file)
            item_hash = sales_data[item]["itemHash"]
            item_definition = await bot.destiny_client.decode_hash(item_hash,"DestinyInventoryItemDefinition")
            item_categories = item_definition["itemCategoryHashes"]
            if 59 in item_categories:
                item_template = templates["Mods"]
                item_template["definition"] = item_definition
                item_template["item_hash"] = item_hash
                mods[str(item_hash)] = item_template
                continue

            if 1 in item_categories:
                item_template = templates["Weapons"]
                with open("data/weapon_stat_arrangement.json", "r", encoding="utf-8") as file:
                    weapon_stat_arrangements = json.load(file)
                for category in item_categories:
                    category = str(category)
                    if category in weapon_stat_arrangements:
                        stat_arrangement = weapon_stat_arrangements[category]
                        break
                    stat_arrangement = weapon_stat_arrangements["Default"]

            elif 20 in item_categories:
                item_template = templates["Armor"]
                stat_arrangement = {"Armor": ["Mobility", "Resilience", "Recovery", "Discipline", "Intellect", "Strength"]}
                classes = {21: "Warlock", 22: "Titan", 23: "Hunter"}
                for category in item_categories:
                    if category in classes:
                        item_template["class"] = classes[category]
                        break
            else:
                continue

            item_template["definition"] = item_definition
            item_template["item_hash"] = item_hash
            item_template["costs"] = sales_data[item]["costs"]
            item_stats = stats_data[item]["stats"]
            item_template = await process_item_stats(bot=bot, item_template=item_template, item_stats=item_stats, stat_arrangement=stat_arrangement)
            item_sockets = sockets_data[item]["sockets"]
            item_template = await process_item_sockets(bot=bot, item_template=item_template, item_sockets=item_sockets)

            if 20 in item_categories:
                armor[str(item_hash)] = item_template
            else:
                weapons[str(item_hash)] = item_template

    except Exception as ex:
        logger.exception("Error processing vendor sales: %s", ex)
        return False
    else:
        destiny_rotation = bot.database["destiny_rotation"]
        destiny_rotation.update_one({"vendor_hash": vendor_hash}, {"$set": {"vendor": data["vendor"]["data"]}}, upsert=True)
        if armor:
            destiny_rotation.update_one({"vendor_hash": vendor_hash},
                                        {"$set": {"armor": armor}},
                                        upsert=True)
        if weapons:
            destiny_rotation.update_one({"vendor_hash": vendor_hash},
                                        {"$set": {"weapons": weapons}},
                                        upsert=True)
        if mods:
            destiny_rotation.update_one({"vendor_hash": vendor_hash},
                                        {"$set": {"mods": mods}},
                                        upsert=True)
        destiny_rotation.update_one({"vendor_hash": vendor_hash},
                                    {"$set": {"date": datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d")}},
                            upsert=True)
        logger.debug("Vendor sales processed")
        return True

async def process_item_sockets(bot: Ehrenbot, item_template: dict, item_sockets) -> dict:
    for socket in item_sockets:
        if not socket.get("plugHash"):
            continue
        plug_hash = socket["plugHash"]
        socket_definition = await bot.destiny_client.decode_hash(plug_hash, "DestinyInventoryItemDefinition")
        socket_type = socket_definition["itemTypeDisplayName"]
        if socket_type not in item_template["sockets"]:
            item_template["sockets"][socket_type] = {}
        socket_name = socket_definition["displayProperties"]["name"]
        socket_description = socket_definition["displayProperties"]["description"]
        socket_dict = {
            "socket_hash": plug_hash,
            "socket_name": socket_name,
            "socket_description": socket_description
        }
        item_template["sockets"][socket_type][socket_name] = socket_dict
    return item_template

async def process_item_stats(bot: Ehrenbot, item_template: dict, item_stats: dict, stat_arrangement: dict) -> dict:
    unsorted_stats = {}
    for stat in item_stats:
        stat = item_stats[stat]
        stat_hash = stat["statHash"]
        stat_value = stat["value"]
        stat_definition = await bot.destiny_client.decode_hash(stat_hash, "DestinyStatDefinition")
        stat_name = stat_definition["displayProperties"]["name"]
        stat = {
            "stat_hash": stat_hash,
            "stat_name": stat_name,
            "value": stat_value
        }
        unsorted_stats[stat_name] = stat
    sorted_stats = {}
    for _stat in stat_arrangement:
        if _stat in unsorted_stats:
            sorted_stats[_stat] = unsorted_stats[_stat]
    item_template["stats"] = sorted_stats
    return item_template

async def vendor_info(bot: Ehrenbot, logger: Logger, vendor_hash: int) -> bool:
    try:
        destiny_rotation = bot.database["destiny_rotation"]
        vendor = await bot.destiny_client.decode_hash(vendor_hash, "DestinyVendorDefinition")
        destiny_rotation.update_one({"vendor_hash": vendor_hash},
                                    {"$set": {"vendor": vendor}}, upsert=True)
    except Exception as ex:
        logger.exception("Error getting vendor info: %s", ex)
    else:
        logger.debug("%d info updated", vendor_hash)
        return True

async def banshee_ada_rotation(bot: Ehrenbot, logger: Logger):
    channel: discord.TextChannel = discord.utils.get(bot.get_all_channels(), name="vendor-sales")
    if not channel:
        logger.error("Failed to find vendor-sales channel")
        return
    logger.info("Starting daily vendor rotation...")
    # Fetch vendor sales and send embeds
    rotation_collection = bot.database["destiny_rotation"]
    vendor_hashes = [672118013, 350061650]
    for vendor_hash in vendor_hashes:
        if not await fetch_vendor_sales(bot=bot, logger=logger, vendor_hash=vendor_hash):
            logger.error("Failed to fetch vendor sales for vendor %s", vendor_hash)
            return
        embed = await vendor_embed(bot=bot, vendor_hash=vendor_hash)
        entry = rotation_collection.find_one({"vendor_hash": vendor_hash})
        if _id := entry.get("message_id"):
            message = await channel.fetch_message(_id)
            await message.edit(content="", embed=embed)
        else:
            await channel.send(content="", embed=embed)
            _id = channel.last_message_id
            rotation_collection.update_one({"vendor_hash": vendor_hash}, {"$set": {"message_id": _id}}, upsert=True)
        logger.debug("Sent embed for vendor %s", vendor_hash)
    logger.info("Daily vendor rotation complete")

async def create_emoji_from_entry(bot: Ehrenbot, logger: Logger, item_hash: int,
                                  collection: Collection, vendor_hash: int = 0) -> Union[discord.Emoji, None]:
    try:
        entry = collection.find_one({"hash": item_hash})
        icon_url = entry["displayProperties"]["icon"]
        name = entry["displayProperties"]["name"]
        # Replace all non-alphanumeric characters with underscores in the middle of the name
        name = name.replace(":", "_").replace("-", "_").replace(".", "_").replace("'", "_").replace("(", "_").replace(")", "_").replace(" ", "_")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://www.bungie.net{icon_url}") as resp:
                if resp.status != 200:
                    raise aiohttp.ClientError(f"Error fetching image: {resp.status} {resp.reason}")
                data = await resp.read()
                emoji = await bot.get_guild(bot.vendor_guild_id).create_custom_emoji(name=name, image=data)
    except aiohttp.ClientError as ex:
        logger.error("%s", ex)
        return None
    else:
        logger.debug("Emoji created for %d", item_hash)
        emoji_collection = bot.database["emojis"]
        emoji_collection.insert_one({"emoji_id": emoji.id, "guild_id": bot.vendor_guild_id, "vendor_hash": vendor_hash})
        return emoji

async def vendor_embed(bot: Ehrenbot, vendor_hash:int) -> discord.Embed:
    match vendor_hash:
        case 672118013:
            bot.vendor_guild_id = 1057709724843397282
            embed = await banshee_embed(bot)
        case 350061650:
            bot.vendor_guild_id = 1057710325631295590
            embed = await ada_embed(bot)
        case _:
            embed = discord.Embed(title="Vendor", description="Vendor not found")

    # Set footer
    current_time = datetime.datetime.now(timezone.utc)
    embed.set_footer(text=f"Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    return embed

async def weapon_embed_field(bot: Ehrenbot, vendor_hash: int) -> str:
    daily_rotation = bot.database["destiny_rotation"].find_one({"vendor_hash": vendor_hash})
    inventory_item_collection = bot.mongo_client["d2manifest_en"]["DestinyInventoryItemDefinition"]
    weapons = daily_rotation["weapons"]
    weapon_string = ""
    for weapon in weapons:
        if weapons[weapon]["definition"]["inventory"]["tierType"] == 6:
            continue
        item_hash = weapons[weapon]["item_hash"]
        item_name = weapons[weapon]["definition"]["displayProperties"]["name"]
        emoji = await create_emoji_from_entry(bot=bot, logger=bot.logger, item_hash=item_hash,
                                              collection=inventory_item_collection, vendor_hash=vendor_hash)
        weapon_string += f"<:{emoji.name}:{emoji.id}> {item_name}\n"
    return weapon_string

async def armor_embed_field(bot: Ehrenbot, vendor_hash: int, category: str) -> str:
    daily_rotation = bot.database["destiny_rotation"].find_one({"vendor_hash": vendor_hash})
    inventory_item_collection = bot.mongo_client["d2manifest_en"]["DestinyInventoryItemDefinition"]
    armor = daily_rotation["armor"]
    armor_string = ""
    for armor_piece in armor:
        if armor[armor_piece]["class"] != category:
            continue
        if armor[armor_piece]["definition"]["inventory"]["tierType"] == 6:
            continue
        item_hash = armor[armor_piece]["item_hash"]
        item_name = armor[armor_piece]["definition"]["displayProperties"]["name"]
        emoji = await create_emoji_from_entry(bot=bot, logger=bot.logger, item_hash=item_hash,
                                              collection=inventory_item_collection, vendor_hash=vendor_hash)
        armor_string += f"<:{emoji.name}:{emoji.id}> {item_name}\n"
    return armor_string

async def mod_embed_field(bot: Ehrenbot, vendor_hash: int) -> str:
    daily_rotation = bot.database["destiny_rotation"].find_one({"vendor_hash": vendor_hash})
    inventory_item_collection = bot.mongo_client["d2manifest_en"]["DestinyInventoryItemDefinition"]
    mods = daily_rotation["mods"]
    mod_string = ""
    for mod in mods:
        item_hash = mods[mod]["item_hash"]
        item_name = mods[mod]["definition"]["displayProperties"]["name"]
        emoji = await create_emoji_from_entry(bot=bot, logger=bot.logger, item_hash=item_hash,
                                              collection=inventory_item_collection, vendor_hash=vendor_hash)
        mod_string += f"<:{emoji.name}:{emoji.id}> {item_name}\n"
    return mod_string

async def banshee_embed(bot: Ehrenbot) -> discord.Embed:
    embed = discord.Embed(title="Banshee-44", description="Banshee-44 is a vendor in the Tower who sells weapons and weapon mods.", color=0x567e9d)
    vendor_hash = 672118013
    embed.set_thumbnail(url="https://www.light.gg/Content/Images/banshee-icon.png")
    embed.set_image(url="https://www.bungie.net/common/destiny2_content/icons/3142923bc72bcd5a769badc26bd8b508.jpg")
    mod_string = await mod_embed_field(bot, vendor_hash)
    embed.add_field(name="Mods", value=mod_string, inline=True)
    weapon_string = await weapon_embed_field(bot, vendor_hash)
    embed.add_field(name="Weapons", value=weapon_string, inline=True)
    return embed

async def ada_embed(bot: Ehrenbot) -> discord.Embed:
    embed = discord.Embed(title="Ada-1", description="Ada-1 is a vendor in the Tower who sells armor and armor mods.")
    vendor_hash = 350061650
    embed.set_thumbnail(url="https://www.light.gg/Content/Images/ada-icon.png")
    embed.set_image(url="https://www.bungie.net/common/destiny2_content/icons/e6a489d1386e2928f9a5a33b775b8f03.jpg")
    mod_string = await mod_embed_field(bot, vendor_hash)
    embed.add_field(name="Mods", value=mod_string, inline=False)
    warlock_string = await armor_embed_field(bot, vendor_hash, "Warlock")
    embed.add_field(name="Warlock", value=warlock_string, inline=False)
    titan_string = await armor_embed_field(bot, vendor_hash, "Titan")
    embed.add_field(name="Titan", value=titan_string, inline=False)
    hunter_string = await armor_embed_field(bot, vendor_hash, "Hunter")
    embed.add_field(name="Hunter", value=hunter_string, inline=False)
    return embed
