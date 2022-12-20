import asyncio
import datetime
import json
from logging import Logger
from typing import Union

import aiohttp
from discord import Embed, Emoji
from pymongo.collection import Collection

from ehrenbot import Ehrenbot
from ehrenbot.utils.exceptions import (BungieMaintenance,
                                       DestinyVendorNotFound, NoBungieResponse)


async def xur_embed(bot: Ehrenbot) -> Embed:
    rotation_collection = bot.database["destiny_rotation"]
    vendor = rotation_collection.find_one({"vendor_hash": 2190858386})
    if not vendor["sales"]:
        raise DestinyVendorNotFound("Xur")
    sorted_sales = vendor["sorted_sales"]
    description = vendor["vendor"]["displayProperties"]["description"]
    embed = Embed(title="Xûr, Agent of the Nine", description=f"\u200b{description}")
    icon_url = vendor["vendor"]["displayProperties"]["icon"]
    embed.set_thumbnail(url=f"https://www.bungie.net/{icon_url}")
    for category in sorted_sales:
        display_items = ""
        for item in sorted_sales[category]:
            display_items += f"{item['displayProperties']['name']}\n"
        if category in ["Exotic Armor", "Exotic Weapon", "Warlock", "Titan", "Hunter"]:
            embed.add_field(name=category, value=f"\u200b{display_items}\u200b", inline=True)
        else:
            embed.add_field(name=category, value=f"\u200b{display_items}\u200b", inline=False)
    return embed


async def check_vendors(bot: Ehrenbot) -> str:
    discord_id = bot.ADMIN_DISCORD_ID
    token_collection = bot.database["destiny_tokens"]
    profile_collection = bot.database["destiny_profiles"]
    token = token_collection.find_one({"discord_id": discord_id})["token"]
    profile = profile_collection.find_one({"discord_id": discord_id})["profile"]
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

    await bot.wait_until_ready()
    status = await check_vendors(bot)
    if status == "No response from Bungie API":
        user = bot.get_user(bot.ADMIN_DISCORD_ID)
        await user.send("No response from Bungie API for daily rotation")
        return False
    if status == "Maintenance":
        while status == "Maintenance":
            bot.logger.info("Bungie API is in maintenance mode, retrying in 5 minutes")
            asyncio.sleep(300)
            status = await check_vendors(bot)
    if status == "OK":
        bot.logger.info("Bungie API is ready for daily rotation")
    return True

async def get_vendor_data(bot: Ehrenbot, vendor_hash: int) -> dict:
    discord_id = bot.ADMIN_DISCORD_ID
    token_collection = bot.database["destiny_tokens"]
    profile_collection = bot.database["destiny_profiles"]
    token = token_collection.find_one({"discord_id": discord_id})["token"]
    profile = profile_collection.find_one({"discord_id": discord_id})["profile"]
    destiny2 = bot.destiny_client.destiny2
    result = {}
    for character_id in profile["character_ids"]:
        response = await destiny2.GetVendor(token=token,
                                            character_id=character_id,
                                            destiny_membership_id=profile["destiny_membership_id"],
                                            membership_type=profile["membership_type"],
                                            vendor_hash=vendor_hash,
                                            components=[402,304,305])
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
        current_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        destiny_rotation = bot.database["destiny_rotation"]
        if destiny_rotation.find_one({"vendor_hash": vendor_hash}):
            date_str = destiny_rotation.find_one({"vendor_hash": vendor_hash})["date"]
            if date_str == current_date:
                logger.info("Vendor rotation already in database")
                return True
        destiny_rotation.update_one({"vendor_hash": vendor_hash}, {"$set": {"armor": [], "weapons": []}})
        data = await get_vendor_data(bot=bot, vendor_hash=vendor_hash)

        modified_data = {"sales": {}, "stats": {}, "sockets": {}}
        for character_id in data:
            sales = data[character_id]["sales"]["data"]
            stats = data[character_id]["itemComponents"]["stats"]["data"]
            sockets = data[character_id]["itemComponents"]["sockets"]["data"]
            modified_data["sales"].update(sales)
            modified_data["stats"].update(stats)
            modified_data["sockets"].update(sockets)

    except NoBungieResponse:
        logger.error("No response from Bungie API")
        return False
    except BungieMaintenance:
        logger.error("Bungie API is in maintenance mode")
        return False
    except DestinyVendorNotFound:
        logger.error("Vendor not found")
        return False
    except Exception as ex:
        logger.error(f"Error: {ex}")
        return False
    else:
        logger.info(f"{vendor_hash} sales modified, processing...")
        return await process_vendor_sales(bot=bot, logger=logger, vendor_hash=vendor_hash, data=modified_data)

# ! armor stats are not updating

async def process_vendor_sales(bot: Ehrenbot, logger: Logger, vendor_hash: int, data: dict) -> bool:
    try:
        classes = {"Warlock": 21,"Titan": 22, "Hunter": 23}
        armor = {}
        armor_stat_arrangement = {"Armor": ["Mobility", "Resilience", "Recovery", "Discipline", "Intellect", "Strength"]}
        weapons = {}
        with open("data/vendor_sale_item.json", "r", encoding="utf-8") as file:
            templates = json.load(file)
        sales_data = data["sales"]
        stats_data = data["stats"]
        sockets_data = data["sockets"]
        for item in sales_data:
            item_hash = sales_data[item]["itemHash"]
            item_definition = await bot.destiny_client.decode_hash(item_hash,"DestinyInventoryItemDefinition")
            item_categories = item_definition["itemCategoryHashes"]
            if 1 in item_categories:
                item_type = "Weapons"
            elif 20 in item_categories:
                item_type = "Armor"
            else:
                continue
            item_costs = sales_data[item]["costs"]
            item_stats = stats_data[item]["stats"]
            item_sockets = sockets_data[item]["sockets"]
            item_template = templates[item_type]

            logger.debug(f"Processing item {item_hash}")
            item_template["definition"] = item_definition
            item_template["definition"]["itemHash"] = item_hash
            item_template["costs"]  = item_costs

            for category, value in classes.items():
                if value in item_categories:
                    item_template["class"] = category
                    break

            if item_type == "Weapons":
                with open("data/weapon_stat_arrangement.json", "r", encoding="utf-8") as file:
                    weapon_stat_arrangements = json.load(file)
                for category in item_categories:
                    if category in weapon_stat_arrangements:
                        stat_arrangement = weapon_stat_arrangements[category]
                        break
                    stat_arrangement = weapon_stat_arrangements["Default"]
            else:
                stat_arrangement = armor_stat_arrangement
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

            for socket in item_sockets:
                if not socket.get("plugHash"):
                    continue
                plug_hash = socket["plugHash"]
                socket_definition = await bot.destiny_client.decode_hash(plug_hash, "DestinyInventoryItemDefinition")
                socket_type = socket_definition["itemTypeDisplayName"]
                if socket_type not in item_template["sockets"].keys():
                    continue
                socket_name = socket_definition["displayProperties"]["name"]
                socket_icon = socket_definition["displayProperties"]["icon"]
                socket_description = socket_definition["displayProperties"]["description"]
                socket = {
                    "socket_hash": plug_hash,
                    "socket_name": socket_name,
                    "socket_icon": socket_icon,
                    "socket_description": socket_description
                }
                item_template["sockets"][socket_type][socket_name] = socket

            item_name = item_template["definition"]["displayProperties"]["name"]
            if item_type == "Armor":
                armor[item_name] = item_template
            else:
                weapons[item_name] = item_template

    except Exception as ex:
        logger.exception(f"Error processing vendor sales: {ex}")
        return False
    else:
        destiny_rotation = bot.database["destiny_rotation"]
        destiny_rotation.update_one({"vendor_hash": vendor_hash},
                            {"$set": {"armor": armor, "weapons": weapons, "date": datetime.utcnow().date()}},
                            upsert=True)
        logger.info("Vendor sales processed")
        return True

async def sort_sales(bot: Ehrenbot, logger: Logger, vendor_hash: int) -> bool:
    try:
        destiny_rotation = bot.database["destiny_rotation"]
        sale_items = destiny_rotation.find_one({"vendor_hash": vendor_hash})
        sales = sale_items["sales"]
        item_categories = {"Repeatable Bounties": 713159888,
                            "Bounties": 1784235469,
                            "Mods": 59, "Weapons": 1,
                            "Exotic Weapon": "exotic weapon", "Exotic Armor": "exotic armor",
                            "Warlock": 21,"Titan": 22, "Hunter": 23,
                            "Sparrows": 43, "Ships": 42,
                            "Packages": 268598612}
        sorted_items = {}

        #TODO: OPTIMIZE THIS
        # ! List comprehension, code:dive python refactoring 2 (hoekstra) 45:10

        for item in sales:
            if item["inventory"].get("tierTypeName") == "Exotic":
                if 1 in item["itemCategoryHashes"]:
                    item["itemCategoryHashes"] = ["exotic weapon"]
                else:
                    item["itemCategoryHashes"] = ["exotic armor"]
            categories = item["itemCategoryHashes"]
            for category in categories:
                if category in item_categories.values():
                    for key, value in item_categories.items():
                        if category == value:
                            if key not in sorted_items:
                                sorted_items[key] = []
                            sorted_items[key].append(item)
        destiny_rotation.update_one({"vendor_hash": vendor_hash}, {"$set": {"sorted_sales": sorted_items}}, upsert=True)
    except Exception as ex:
        logger.exception(f"Error sorting sales: {ex}")
    else:
        logger.info(f"{vendor_hash} sales sorted")
        return True

async def vendor_info(bot: Ehrenbot, logger: Logger, vendor_hash: int) -> bool:
    try:
        destiny_rotation = bot.database["destiny_rotation"]
        vendor = await bot.destiny_client.decode_hash(vendor_hash, "DestinyVendorDefinition")
        destiny_rotation.update_one({"vendor_hash": vendor_hash},
                                    {"$set": {"vendor": vendor}}, upsert=True)
    except Exception as ex:
        logger.exception(f"Error getting vendor info: {ex}")
    else:
        logger.info(f"{vendor_hash} info updated")
        return True

async def create_emoji_from_entry(bot: Ehrenbot, logger: Logger, item_hash: int, collection: Collection) -> Union[Emoji, None]:
    try:
        collection.find_one({"hash": item_hash})
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://www.bungie.net/common/destiny2_content/icons/{hash}.png") as resp:
                if resp.status != 200:
                    raise aiohttp.ClientError(f"Error fetching image: {resp.status} {resp.reason}")
                data = await resp.read()
                emoji = await bot.get_guild(bot.GUILD_ID).create_custom_emoji(name=str(hash), image=data)
    except aiohttp.ClientError as ex:
        logger.error(f"{ex}")
        return None
    else:
        logger.info(f"Emoji created for {item_hash}")
        return emoji
