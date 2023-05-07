import datetime
from logging import Logger

import discord

from ehrenbot import Ehrenbot
from .embeds import vendor_embed
from .item_processing import fetch_vendor_sales
from .shaders import get_missing_shaders

async def vendor_rotations(bot: Ehrenbot, logger: Logger, vendor_hash: int):
    channel: discord.TextChannel = discord.utils.get(
        bot.get_all_channels(), name="vendor-sales"
    )
    if not channel:
        logger.error("Failed to find vendor-sales channel")
        return
    logger.info("Starting daily vendor rotation...")
    # Fetch vendor sales and send embeds
    rotation_collection = bot.database["destiny_rotation"]
    if not await fetch_vendor_sales(bot=bot, logger=logger, vendor_hash=vendor_hash):
        logger.error("Failed to fetch vendor sales for vendor %s", vendor_hash)
        return
    entry = rotation_collection.find_one({"vendor_hash": vendor_hash})
    embed = await vendor_embed(bot=bot, vendor_hash=vendor_hash)
    if _id := entry.get("message_id"):
        message = await channel.fetch_message(_id)
        await message.edit(content="", embed=embed)
    else:
        await channel.send(content="", embed=embed)
        _id = channel.last_message_id
        rotation_collection.update_one(
            {"vendor_hash": vendor_hash}, {"$set": {"message_id": _id}}, upsert=True
        )
    logger.debug("Sent embed for vendor %s", vendor_hash)

    if vendor_hash == 350061650:  # Ada-1 for shaders notification
        logger.debug("Notifying members for missing shaders...")
        # Get reset date
        reset_date = entry["vendor"]["nextRefreshDate"]
        # Parse reset date
        reset_date = datetime.datetime.strptime(reset_date, "%Y-%m-%dT%H:%M:%SZ")
        with open("data/notify-shaders.csv", "r", encoding="utf-8") as file:
            notify_shaders = file.read().splitlines()
        for member_id in notify_shaders:
            # Check if member is in Main server
            member = await bot.fetch_user(member_id)
            if member.mutual_guilds == []:
                notify_shaders.remove(member_id)
                continue
            missing_shaders = await get_missing_shaders(
                bot=bot, logger=logger, discord_id=int(member_id)
            )
            if missing_shaders == "No profile found for this user.":
                notify_shaders.remove(member_id)
                continue
            if missing_shaders == "You have all shaders!":
                continue  # Placeholder
            if missing_shaders == "No shaders are being sold that you are missing!":
                continue
            if missing_shaders == []:
                continue
            shaders_text = "\n".join(missing_shaders)

            await member.send(
                "You are missing shaders from Ada-1! Go pick them up before it's too late!\n\n"
                f"{shaders_text}\n\n"
                f"Reset: **{reset_date.strftime('%d-%m-%y %H:%M')} UTC**\n"
            )
            logger.debug("Sent notification to %s (%s).", member_id, member.name)

        # Update notify-mods.csv
        with open("data/notify-shaders.csv", "w", encoding="utf-8") as file:
            for member_id in notify_shaders:
                file.write(f"{member_id}\n")

        logger.info("Vendor rotation complete!")
