import asyncio
import datetime
from logging import Logger

from discord import Embed

from ehrenbot import Ehrenbot
from ehrenbot.utils.exceptions import (BungieMaintenance,
                                       DestinyVendorNotFound, NoBungieResponse)


async def daily_embed(bot: Ehrenbot) -> Embed:
    pass

async def banshee_embed(bot: Ehrenbot) -> Embed:
    pass

async def ada_embed(bot: Ehrenbot) -> Embed:
    pass

async def weekly_embed(bot: Ehrenbot) -> Embed:
    pass

async def tess_embed(bot: Ehrenbot) -> Embed:
    pass

async def xur_embed(bot: Ehrenbot) -> Embed:
    rotation_collection = bot.database["destiny_rotation"]
    sales = rotation_collection.find_one({"vendor_hash": 2190858386})
    if not sales:
        raise DestinyVendorNotFound("Xur")
    sorted_sales = sales["sorted_sales"]
    location = sales["location"]
    embed = Embed(title="Xûr, Agent of the Nine", description=f"Xûr is currently located at {location}")


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
                                            components=[402])
        if not response:
            raise NoBungieResponse
        if response["ErrorCode"] == 5:
            raise BungieMaintenance
        if response["ErrorCode"] == 1627:
            raise DestinyVendorNotFound
        sale_data = response["Response"]["sales"]["data"]
        result[character_id] = sale_data
    return result

async def vendor_sales(bot: Ehrenbot, logger: Logger, vendor_hash: int) -> bool:
    try:
        current_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        destiny_rotation = bot.database["destiny_rotation"]
        if destiny_rotation.find_one({"vendor_hash": vendor_hash}):
            date_str = destiny_rotation.find_one({"vendor_hash": vendor_hash})["date"]
            if date_str == current_date:
                logger.info("Vendor rotation already in database")
                return True
        sales = await get_vendor_data(bot=bot, vendor_hash=vendor_hash)
        sales_items = []
        for character_id in sales:
            items = sales[character_id]
            for item in items:
                item = items[item]
                item_hash = int(item["itemHash"])
                item = await bot.destiny_client.decode_hash(item_hash, "DestinyInventoryItemDefinition")
                if item not in sales_items:
                    sales_items.append(item)
        destiny_rotation.update_one({"vendor_hash": vendor_hash},
                                    {"$set": {"sales": sales_items, "date": current_date}},
                                    upsert=True)
    except NoBungieResponse:
        logger.error("No response from Bungie API")
    except BungieMaintenance:
        logger.error("Bungie API is in maintenance mode")
    except DestinyVendorNotFound:
        logger.error("Vendor not found")
    else:
        logger.info(f"{vendor_hash} sales updated")
        return await sort_sales(bot=bot, logger=logger, vendor_hash=vendor_hash)

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

        # ! OPTIMIZE THIS

        for item in sales:
            if item["inventory"].get("tierTypeName") == "Exotic":
                if 1 in item["itemCategoryHashes"]:
                    item["itemCategoryHashes"] = ["exotic weapon"]
                else:
                    item["itemCategoryHashes"] = ["exotic armor"]
            categories = item["itemCategoryHashes"]
        # Consider iterating with .items()
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
