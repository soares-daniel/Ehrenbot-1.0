import asyncio

from ehrenbot import Ehrenbot
from ehrenbot.utils.exceptions import (BungieMaintenance, DestinyVendorNotFound, NoBungieResponse)

async def check_vendors(bot: Ehrenbot) -> str:
    discord_id = bot.ADMIN_DISCORD_ID
    token_collection = bot.database["destiny_tokens"]
    profile_collection = bot.database["members"]
    token = token_collection.find_one({"discord_id": discord_id})["token"]
    profile = profile_collection.find_one({"discord_id": discord_id})["destiny_profile"]
    destiny2 = bot.destiny_client.destiny2
    response = await destiny2.GetVendors(
        token=token,
        character_id=profile["character_ids"][0],
        destiny_membership_id=profile["destiny_membership_id"],
        membership_type=profile["membership_type"],
        components=[400],
    )
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
            bot.logger.warning(
                "Bungie API is in maintenance mode, retrying in 5 minutes"
            )
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
        response = await destiny2.GetVendor(
            token=token,
            character_id=character_id,
            destiny_membership_id=profile["destiny_membership_id"],
            membership_type=profile["membership_type"],
            vendor_hash=vendor_hash,
            components=[400, 402, 304, 305],
        )
        if not response:
            raise NoBungieResponse
        if response["ErrorCode"] == 5:
            raise BungieMaintenance
        if response["ErrorCode"] == 1627:
            raise DestinyVendorNotFound
        result[character_id] = response["Response"]
    return result
