import asyncio
import datetime
import json
from datetime import timezone
from logging import Logger
from typing import Union

import aiohttp
from discord import Embed, Emoji
from pymongo.collection import Collection

from ehrenbot import Ehrenbot
from ehrenbot.utils.exceptions import (BungieMaintenance,
                                       DestinyVendorNotFound, NoBungieResponse)


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
        current_date = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d")
        destiny_rotation = bot.database["destiny_rotation"]
        if entry := destiny_rotation.find_one({"vendor_hash": vendor_hash}):
            date_str = entry["date"]
            if date_str == current_date:
                logger.info("Vendor rotation already in database")
                return True
        destiny_rotation.update_one({"vendor_hash": vendor_hash}, {"$set": {"armor": [], "weapons": []}}, upsert=True)
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
        logger.warning("Vendor %d not found", vendor_hash)
        return False
    except Exception as ex:
        logger.error("Error: %s", ex)
        return False
    else:
        logger.info("%d sales modified, processing...", vendor_hash)
        return await process_vendor_sales(bot=bot, logger=logger, vendor_hash=vendor_hash, data=modified_data)

# ! armor stats are not updating

async def process_vendor_sales(bot: Ehrenbot, logger: Logger, vendor_hash: int, data: dict) -> bool:
    try:
        classes = {"Warlock": 21,"Titan": 22, "Hunter": 23}
        armor = {}
        armor_stat_arrangement = {"Armor": ["Mobility", "Resilience", "Recovery", "Discipline", "Intellect", "Strength"]}
        weapons = {}
        mods = {}
        with open("data/vendor_sale_item.json", "r", encoding="utf-8") as file:
            templates = json.load(file)
        sales_data = data["sales"]
        stats_data = data["stats"]
        sockets_data = data["sockets"]
        for item in sales_data:
            item_hash = sales_data[item]["itemHash"]
            item_definition = await bot.destiny_client.decode_hash(item_hash,"DestinyInventoryItemDefinition")
            item_categories = item_definition["itemCategoryHashes"]
            if 59 in item_categories:
                item_type = "Mods"
                mod_name = item_definition["displayProperties"]["name"]
                mod_info = {
                    "item_hash": item_hash,
                    "category_hash": 59,
                    "definition": item_definition,
                    "costs": sales_data[item]["costs"],
                }
                mods[mod_name] = mod_info
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

            logger.debug("Processing item %d", item_hash)
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
        logger.exception("Error processing vendor sales: %s", ex)
        return False
    else:
        destiny_rotation = bot.database["destiny_rotation"]
        destiny_rotation.update_one({"vendor_hash": vendor_hash},
                            {"$set": {"armor": armor, "weapons": weapons, "mods": mods, "date": datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d")}},
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
        logger.exception("Error sorting sales: %s", ex)
    else:
        logger.info("%d sales sorted", vendor_hash)
        return True

async def vendor_info(bot: Ehrenbot, logger: Logger, vendor_hash: int) -> bool:
    try:
        destiny_rotation = bot.database["destiny_rotation"]
        vendor = await bot.destiny_client.decode_hash(vendor_hash, "DestinyVendorDefinition")
        destiny_rotation.update_one({"vendor_hash": vendor_hash},
                                    {"$set": {"vendor": vendor}}, upsert=True)
    except Exception as ex:
        logger.exception("Error getting vendor info: %s", ex)
    else:
        logger.info("%d info updated", vendor_hash)
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
        logger.error("%s", ex)
        return None
    else:
        logger.info("Emoji created for %d", item_hash)
        return emoji

async def vendor_embed(bot: Ehrenbot, vendor_hash:int) -> Embed:
    match vendor_hash:
        case 2190858386:
            embed = await xur_embed(bot)
        case 672118013:
            embed = await banshee_embed(bot)
        case 350061650:
            embed = await ada_embed(bot)
        case default:
            embed = Embed(title="Vendor", description="Vendor not found")
    current_time = datetime.datetime.now(timezone.utc)
    embed.set_footer(text=f"Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    return embed

async def xur_embed(bot: Ehrenbot) -> Embed:
    return Embed(title="Xûr, Agent of the Nine", description="Xûr is currently not in the tower")

async def banshee_embed(bot: Ehrenbot) -> Embed:
    return Embed(title="Banshee-44", description="Banshee-44 is a vendor in the Tower who sells weapons and weapon mods.")

async def ada_embed(bot: Ehrenbot) -> Embed:
    return Embed(title="Ada-1", description="Ada-1 is a vendor in the Tower who sells armor and armor mods.")

async def get_missing_mods(bot: Ehrenbot, logger: Logger, discord_id: int) -> bool:
    try:
        logger.debug("Getting missing mods for %d...", discord_id)

        # Get all collectibles
        profiles = bot.database["destiny_profiles"]
        profile = profiles.find_one({"discord_id": discord_id})
        r = await bot.destiny_client.destiny2.GetProfile(
            destiny_membership_id=profile["profile"]["destiny_membership_id"],
            membership_type=profile["profile"]["membership_type"],
            components=[800])
        collectibles = r["Response"]["profileCollectibles"]["data"]["collectibles"]
        not_acquired = []

        # Get not acquired collectibles
        for collectible in collectibles:
            if collectibles[collectible]["state"]%2 == 1:
                not_acquired.append(int(collectible))
        # Get mods from not acquired collectibles
        final = []
        mods = bot.database["destiny_mods"]
        for mod in mods.find():
            if mod["hash"] in not_acquired and mod["itemHash"] != 2527938402:
                final.append(mod["itemHash"])
        # Get available mods
        if final == []:
            return {"message": "You have all mods!"}
        rotation_collection = bot.database["destiny_rotation"]
        banshee_mods = rotation_collection.find_one({"vendor_hash": 672118013})["mods"]
        ada_mods = rotation_collection.find_one({"vendor_hash": 350061650})["mods"]
        missing_mods = {672118013: [], 350061650: []}
        for mod in banshee_mods:
            mod = banshee_mods[mod]
            if mod["item_hash"] in final:
                missing_mods[672118013].append(mod["definition"]["displayProperties"]["name"])
        for mod in ada_mods:
            mod = ada_mods[mod]
            if mod["item_hash"] in final:
                missing_mods[350061650].append(mod["definition"]["displayProperties"]["name"])
    except Exception as ex:
        logger.exception("Error getting missing mods: %s", ex)
        return {672118013: [], 350061650: []}
    else:
        logger.info("Missing mods sent to %d", discord_id)
        return missing_mods
