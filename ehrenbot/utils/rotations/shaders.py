from logging import Logger

import discord

from ehrenbot import Ehrenbot
from .embeds import create_emoji_from_entry


async def get_missing_shaders(bot: Ehrenbot, logger: Logger, discord_id: int) -> bool:
    try:
        member = bot.get_user(discord_id)
        logger.debug("Getting missing mods for %d (%s)...", discord_id, member.name)

        # Get all collectibles
        profile_collection = bot.database["members"]
        profile = profile_collection.find_one({"discord_id": discord_id})
        if not profile:
            logger.info(
                "No profile found for %d (%s). Removing from list",
                discord_id,
                member.name,
            )
            return "No profile found for this user."
        if not profile["destiny_profile"]:
            logger.info(
                "No destiny profile found for %d (%s). Removing from list",
                discord_id,
                member.name,
            )
            return "No profile found for this user."
        response = await bot.destiny_client.destiny2.GetProfile(
            destiny_membership_id=profile["destiny_profile"]["destiny_membership_id"],
            membership_type=profile["destiny_profile"]["membership_type"],
            components=[800],
        )
        collectibles = response["Response"]["profileCollectibles"]["data"][
            "collectibles"
        ]
        not_acquired = []

        # Get all not acquired collectibles
        not_acquired = [
            int(collectible)
            for collectible in collectibles
            if collectibles[collectible]["state"] % 2 == 1
        ]

        # Convert to itemHashes and filter out shaders
        item_hashes = []
        shaders = bot.database["destiny_shaders"]
        for collectible in not_acquired:
            response = await bot.destiny_client.decode_hash(
                collectible, "DestinyCollectibleDefinition"
            )
            item_hash = response["itemHash"]
            item_hashes.append(item_hash)

        # Get all shaders
        missing_shader = []
        for shader in shaders.find():
            if shader["hash"] in item_hashes:
                missing_shader.append(shader["hash"])
        if not missing_shader:
            logger.info("No missing shaders for %d (%s)", discord_id, member.name)
            return "You have all shaders!"

        # Get available shaders
        rotation_collection = bot.database["destiny_rotation"]
        sold_shaders = rotation_collection.find_one({"vendor_hash": 350061650})[
            "shaders"
        ]
        final = []
        for shader in sold_shaders:
            if int(shader) in missing_shader:
                shader = sold_shaders[shader]
                item_name = shader["definition"]["displayProperties"]["name"]
                emoji: discord.Emoji = await create_emoji_from_entry(
                    bot=bot, logger=logger, item_definition=shader["definition"]
                )
                final.append(f"<:{emoji.name}:{emoji.id}> {item_name}")
        if not final:
            logger.info(
                "No missing shaders are being sold for %d (%s)", discord_id, member.name
            )
            return "No shaders are being sold that you are missing!"

    except Exception as ex:
        logger.exception("Error getting missing mods: %s", ex)
        return {}
    else:
        return final
