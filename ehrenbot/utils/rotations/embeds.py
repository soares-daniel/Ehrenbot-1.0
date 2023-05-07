import datetime
from datetime import timezone
from logging import Logger
from typing import Union

import aiohttp
import discord
from discord.utils import find

from ehrenbot import Ehrenbot


async def create_emoji_from_entry(
    bot: Ehrenbot, logger: Logger, item_definition: dict
) -> Union[discord.Emoji, None]:
    try:
        item_hash = item_definition["hash"]
        item_name = item_definition["displayProperties"]["name"]
        if 20 in item_definition["itemCategoryHashes"]:
            item_name = item_hash  # Armor share name often, use the hash instead
        else:
            chars_to_replace = ":.-'() "

            for char in chars_to_replace:
                item_name = item_name.replace(char, "_")

        item_icon = item_definition["displayProperties"]["icon"]
        # Replace all non-alphanumeric characters with underscores in the middle of the name

        # Check if the emoji already exists
        emojis = await bot.get_guild(bot.vendor_guild_id).fetch_emojis()
        emoji = find(lambda e: e.name == item_name, emojis)

        if emoji:
            logger.debug("Emoji already exists for %d", item_hash)
            return emoji
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://www.bungie.net{item_icon}") as resp:
                if resp.status != 200:
                    raise aiohttp.ClientError(
                        f"Error fetching image: {resp.status} {resp.reason}"
                    )
                data = await resp.read()
                emoji = await bot.get_guild(bot.vendor_guild_id).create_custom_emoji(
                    name=item_name, image=data
                )
    except Exception as ex:
        logger.exception(
            "Error creating emoji with item_definition %s:\n %s", item_definition, ex
        )
        emoji = find(lambda e: e.name == "missing_icon_d2", emojis)
    else:
        logger.debug("Emoji created for %d", item_hash)
    return emoji


async def vendor_embed(bot: Ehrenbot, vendor_hash: int) -> discord.Embed:
    match vendor_hash:
        case 672118013:
            bot.vendor_guild_id = 1057709724843397282
            embed = await banshee_embed(bot)
        case 350061650:
            bot.vendor_guild_id = 1057711135668850688
            embed = await ada_embed(bot)
        case _:
            embed = discord.Embed(title="Vendor", description="Vendor not found")

    # Set footer
    current_time = datetime.datetime.now(timezone.utc)
    embed.set_footer(
        text=f"Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    return embed


async def weapon_embed_field(bot: Ehrenbot, vendor_hash: int) -> str:
    daily_rotation = bot.database["destiny_rotation"].find_one(
        {"vendor_hash": vendor_hash}
    )
    weapons = daily_rotation["weapons"]
    weapon_string = ""
    for weapon in weapons:
        if weapons[weapon]["definition"]["inventory"]["tierType"] == 6:
            continue
        item_name = weapons[weapon]["definition"]["displayProperties"]["name"]
        emoji: discord.Emoji = await create_emoji_from_entry(
            bot=bot,
            logger=bot.logger,
            item_definition=weapons[weapon]["definition"],
        )
        weapon_string += f"<:{emoji.name}:{emoji.id}> {item_name}\n"
    return weapon_string


async def armor_embed_field(bot: Ehrenbot, vendor_hash: int, category: str) -> str:
    daily_rotation = bot.database["destiny_rotation"].find_one(
        {"vendor_hash": vendor_hash}
    )
    armor = daily_rotation["armor"]
    sort_to = ["Helmet", "Gauntlets", "Chest Armor", "Leg Armor", "Class Item"]
    # Create a dictionary that maps each item_type to its sort order
    type_order = {type: i for i, type in enumerate(sort_to)}

    # Sort the armor dictionary based on the item_type sort order
    armor = dict(
        sorted(armor.items(), key=lambda item: type_order[item[1]["item_type"]])
    )

    armor_string = ""
    for armor_piece in armor:
        if armor[armor_piece]["class"] != category:
            continue
        if armor[armor_piece]["definition"]["inventory"]["tierType"] == 6:
            continue
        item_name = armor[armor_piece]["definition"]["displayProperties"]["name"]
        emoji: discord.Emoji = await create_emoji_from_entry(
            bot=bot,
            logger=bot.logger,
            item_definition=armor[armor_piece]["definition"],
        )
        armor_string += f"<:{emoji.name}:{emoji.id}> {item_name}\n"
    return armor_string


async def shader_embed_field(bot: Ehrenbot, vendor_hash: int) -> str:
    daily_rotation = bot.database["destiny_rotation"].find_one(
        {"vendor_hash": vendor_hash}
    )
    shaders = daily_rotation["shaders"]
    shader_string = ""
    for shader in shaders:
        item_name = shaders[shader]["definition"]["displayProperties"]["name"]
        emoji: discord.Emoji = await create_emoji_from_entry(
            bot=bot, logger=bot.logger, item_definition=shaders[shader]["definition"]
        )
        shader_string += f"<:{emoji.name}:{emoji.id}> {item_name}\n"
    return shader_string


async def banshee_embed(bot: Ehrenbot) -> discord.Embed:
    # Purge old emojis
    vendor_guild = bot.get_guild(bot.vendor_guild_id)
    for emoji in vendor_guild.emojis:
        await vendor_guild.delete_emoji(emoji)
    embed = discord.Embed(
        title="Banshee-44",
        description="Banshee-44 has lived many lives. As master weaponsmith for the Tower, he supplies Guardians with only the best.",
        color=0x567E9D,
    )
    vendor_hash = 672118013
    embed.set_thumbnail(url="https://www.light.gg/Content/Images/banshee-icon.png")
    embed.set_image(
        url="https://www.bungie.net/common/destiny2_content/icons/3142923bc72bcd5a769badc26bd8b508.jpg"
    )
    weapon_string = await weapon_embed_field(bot, vendor_hash)
    embed.add_field(name="Weapons", value=weapon_string, inline=True)
    return embed


async def ada_embed(bot: Ehrenbot) -> discord.Embed:
    # Purge old emojis
    vendor_guild = bot.get_guild(bot.vendor_guild_id)
    for emoji in vendor_guild.emojis:
        await vendor_guild.delete_emoji(emoji)
    embed = discord.Embed(
        title="Ada-1",
        description="Advanced Prototype Exo and warden of the Black Armory.",
    )
    vendor_hash = 350061650
    embed.set_thumbnail(url="https://www.light.gg/Content/Images/ada-icon.png")
    embed.set_image(
        url="https://www.bungie.net/common/destiny2_content/icons/e6a489d1386e2928f9a5a33b775b8f03.jpg"
    )
    shader_string = await shader_embed_field(bot, vendor_hash)
    embed.add_field(name="Shaders", value=shader_string, inline=True)
    warlock_string = await armor_embed_field(bot, vendor_hash, "Warlock")
    embed.add_field(name="Warlock", value=warlock_string, inline=False)
    titan_string = await armor_embed_field(bot, vendor_hash, "Titan")
    embed.add_field(name="Titan", value=titan_string, inline=False)
    hunter_string = await armor_embed_field(bot, vendor_hash, "Hunter")
    embed.add_field(name="Hunter", value=hunter_string, inline=False)
    return embed
