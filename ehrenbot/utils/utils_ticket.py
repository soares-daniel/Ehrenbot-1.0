from logging import Logger
from typing import Union

import discord

from ehrenbot import Ehrenbot


def create_ticket_embed(ticket: dict, author: Union[discord.Member, discord.User]) -> discord.Embed:
    embed = discord.Embed(title=ticket["title"], color=discord.Color.gold())
    embed.set_thumbnail(url=author.display_avatar.url)
    embed.add_field(value=ticket["ticket_id"], name="Id", inline=True)
    embed.add_field(name="Status", value=ticket["status"], inline=True)
    embed.add_field(name="User", value=author.mention, inline=False)
    embed.add_field(name="Category", value=ticket["category"], inline=False)
    embed.add_field(name="Description", value=ticket["description"], inline=False)
    return embed


async def set_ticket_status(bot: Ehrenbot, embed: discord.Embed, status: str) -> discord.Embed:
    status_color = {
        "Open": discord.Color.gold(),
        "In Work": discord.Color.green(),
        "Closed": discord.Color.red(),
    }
    status_field = [field for field in embed.fields if field.name == "Status"][0]
    status_field.value = status
    embed.color = status_color[status]
    user = embed.fields[2].value
    ticket_collection = bot.database["destiny_tickets"]
    ticket_id = int(embed.fields[0].value)
    ticket_entry: dict = ticket_collection.find_one({"ticket_id": ticket_id})
    user_id: int = ticket_entry["discord_id"]
    user = bot.get_user(user_id)
    await user.send(f"Your ticket status has been updated to **{status}**", delete_after=3600)
    return embed


def get_ticket_entry(bot: Ehrenbot, logger: Logger, ticket_id: int) -> dict:
    try:
        ticket_collection = bot.database["destiny_tickets"]
        ticket_entry: dict = ticket_collection.find_one({"ticket_id": ticket_id})
        if ticket_entry is None:
            raise Exception(f"Ticket {ticket_id} not found")
        return ticket_entry
    except Exception as ex:
        logger.error("%s", ex)
        return


# Syncs the ticket embeds and updates the database
async def sync_ticket(bot: Ehrenbot, logger: Logger, interaction: discord.Interaction, ticket_id: int, embed: discord.Embed) -> None:
    ticket_entry = get_ticket_entry(bot, logger, ticket_id)
    if ticket_entry is None:
        await interaction.followup.send("Ticket not found, please contact admin.", ephemeral=True, delete_after=5)
        return
    guild = bot.get_guild(782316238247559189)
    admin_channel: discord.TextChannel = discord.utils.get(guild.channels, name="📮｜admin-tickets")  # type: ignore
    admin_message = await admin_channel.fetch_message(ticket_entry["admin_message_id"])
    user = bot.get_user(ticket_entry["discord_id"])
    user_message = await user.fetch_message(ticket_entry["user_message_id"])
    await admin_message.edit(embed=embed)
    await user_message.edit(embed=embed)
    ticket: dict = ticket_entry["ticket"]
    for field in embed.fields:
        if field.name == "Status":
            ticket["status"] = field.value
        if field.name == "Edit":
            ticket["edit"] = field.value
    bot.database["destiny_tickets"].update_one({"ticket_id": ticket_id}, {"$set": {"ticket": ticket}})
