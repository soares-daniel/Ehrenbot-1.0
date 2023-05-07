import datetime
import json
from logging import Logger

from ehrenbot import Ehrenbot
from ehrenbot.utils.exceptions import (
    BungieMaintenance,
    DestinyVendorNotFound,
    NoBungieResponse,
)

from .vendor_data import get_vendor_data


async def fetch_vendor_sales(bot: Ehrenbot, logger: Logger, vendor_hash: int) -> bool:
    try:
        current_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        destiny_rotation = bot.database["destiny_rotation"]
        if entry := destiny_rotation.find_one({"vendor_hash": vendor_hash}):
            date_str = entry.get("date")
            if date_str == current_date:
                logger.info("Vendor rotation already in database")
                return True
        destiny_rotation.update_one(
            {"vendor_hash": vendor_hash},
            {"$set": {"armor": [], "weapons": []}},
            upsert=True,
        )
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
        return await process_vendor_sales(
            bot=bot, logger=logger, vendor_hash=vendor_hash, data=modified_data
        )


async def process_vendor_sales(
    bot: Ehrenbot, logger: Logger, vendor_hash: int, data: dict
) -> bool:
    try:
        armor = {}
        weapons = {}
        mods = {}
        shaders = {}
        sales_data = data["sales"]
        stats_data = data["stats"]
        sockets_data = data["sockets"]
        for item in sales_data:
            templates = {}
            with open("data/vendor_sale_item.json", "r", encoding="utf-8") as file:
                templates = json.load(file)
            item_hash = sales_data[item]["itemHash"]
            item_definition = await bot.destiny_client.decode_hash(
                item_hash, "DestinyInventoryItemDefinition"
            )
            item_categories = item_definition["itemCategoryHashes"]
            if 59 in item_categories:
                item_template = templates["Mods"]
                item_template["definition"] = item_definition
                item_template["item_hash"] = item_hash
                mods[str(item_hash)] = item_template
                continue

            if 41 in item_categories:
                item_template = templates["Shaders"]
                item_definition = await bot.destiny_client.decode_hash(
                    item_hash, "DestinyInventoryItemDefinition"
                )
                item_hash = sales_data[item]["itemHash"]
                item_template["definition"] = item_definition
                item_template["item_hash"] = item_hash
                shaders[str(item_hash)] = item_template
                continue

            if 1 in item_categories:
                item_template = templates["Weapons"]
                with open(
                    "data/weapon_stat_arrangement.json", "r", encoding="utf-8"
                ) as file:
                    weapon_stat_arrangements = json.load(file)
                for category in item_categories:
                    category = str(category)
                    if category in weapon_stat_arrangements:
                        stat_arrangement = weapon_stat_arrangements[category]
                        break
                    stat_arrangement = weapon_stat_arrangements["Default"]

            elif 20 in item_categories:
                item_template = templates["Armor"]
                stat_arrangement = {
                    "Armor": [
                        "Mobility",
                        "Resilience",
                        "Recovery",
                        "Discipline",
                        "Intellect",
                        "Strength",
                    ]
                }
                item_template["item_type"] = item_definition["itemTypeDisplayName"]
                # Specific armor types for classes
                if item_template["item_type"] in [
                    "Warlock Bond",
                    "Titan Mark",
                    "Hunter Cloak",
                ]:
                    item_template["item_type"] = "Class Item"
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
            item_template = await process_item_stats(
                bot=bot,
                item_template=item_template,
                item_stats=item_stats,
                stat_arrangement=stat_arrangement,
            )
            item_sockets = sockets_data[item]["sockets"]
            item_template = await process_item_sockets(
                bot=bot, item_template=item_template, item_sockets=item_sockets
            )

            if 20 in item_categories:
                armor[str(item_hash)] = item_template
            else:
                weapons[str(item_hash)] = item_template

    except Exception as ex:
        logger.exception("Error processing vendor sales: %s", ex)
        return False
    else:
        destiny_rotation = bot.database["destiny_rotation"]
        destiny_rotation.update_one(
            {"vendor_hash": vendor_hash},
            {"$set": {"vendor": data["vendor"]["data"]}},
            upsert=True,
        )
        if armor:
            destiny_rotation.update_one(
                {"vendor_hash": vendor_hash}, {"$set": {"armor": armor}}, upsert=True
            )
        if weapons:
            destiny_rotation.update_one(
                {"vendor_hash": vendor_hash},
                {"$set": {"weapons": weapons}},
                upsert=True,
            )
        if mods:
            destiny_rotation.update_one(
                {"vendor_hash": vendor_hash}, {"$set": {"mods": mods}}, upsert=True
            )
        if shaders:
            destiny_rotation.update_one(
                {"vendor_hash": vendor_hash},
                {"$set": {"shaders": shaders}},
                upsert=True,
            )
        destiny_rotation.update_one(
            {"vendor_hash": vendor_hash},
            {
                "$set": {
                    "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
                }
            },
            upsert=True,
        )
        logger.debug("Vendor sales processed")
        return True


async def process_item_sockets(
    bot: Ehrenbot, item_template: dict, item_sockets
) -> dict:
    for socket in item_sockets:
        if not socket.get("plugHash"):
            continue
        plug_hash = socket["plugHash"]
        socket_definition = await bot.destiny_client.decode_hash(
            plug_hash, "DestinyInventoryItemDefinition"
        )
        socket_type = socket_definition["itemTypeDisplayName"]
        if socket_type not in item_template["sockets"]:
            item_template["sockets"][socket_type] = {}
        socket_name = socket_definition["displayProperties"]["name"]
        socket_description = socket_definition["displayProperties"]["description"]
        socket_dict = {
            "socket_hash": plug_hash,
            "socket_name": socket_name,
            "socket_description": socket_description,
        }
        item_template["sockets"][socket_type][socket_name] = socket_dict
    return item_template


async def process_item_stats(
    bot: Ehrenbot, item_template: dict, item_stats: dict, stat_arrangement: dict
) -> dict:
    unsorted_stats = {}
    for stat in item_stats:
        stat = item_stats[stat]
        stat_hash = stat["statHash"]
        stat_value = stat["value"]
        stat_definition = await bot.destiny_client.decode_hash(
            stat_hash, "DestinyStatDefinition"
        )
        stat_name = stat_definition["displayProperties"]["name"]
        stat = {"stat_hash": stat_hash, "stat_name": stat_name, "value": stat_value}
        unsorted_stats[stat_name] = stat
    sorted_stats = {}
    for _stat in stat_arrangement:
        if _stat in unsorted_stats:
            sorted_stats[_stat] = unsorted_stats[_stat]
    item_template["stats"] = sorted_stats
    return item_template
