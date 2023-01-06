# pylint: disable=unused-argument,missing-timeout
import logging
from logging import Logger

import discord
import requests
from discord.ext import commands

from ehrenbot import Ehrenbot
from ehrenbot.utils.utils_ticket import (create_ticket_embed,
                                         set_ticket_status, sync_ticket)
from settings import BUNGIE_API_KEY


class Ticket(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.persistent_added = False
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """ Add persistent views to tickets on startup. """
        if not self.persistent_added:
            self.bot.add_view(TicketSelect(bot=self.bot, logger=self.logger))
            ticket_collection = self.bot.database["destiny_tickets"]
            for ticket in ticket_collection.find():
                user_message_id: int = ticket.get("user_message_id")
                admin_message_id: int = ticket.get("admin_message_id")
                ticket_status: str = ticket["ticket"]["status"]
                if ticket_status != "Closed":
                    if ticket["ticket"]["category"] == "Clan Join Request":
                        self.bot.add_view(ClanRequestView(bot=self.bot, logger=self.logger), message_id=admin_message_id)
                    else:
                        self.bot.add_view(view=TicketAdminView(bot=self.bot, logger=self.logger), message_id=admin_message_id)
                        self.bot.add_view(view=TicketUserView(bot=self.bot, logger=self.logger), message_id=user_message_id)

    @commands.slash_command(name="ticket_system", description="Initializes the ticket system")
    async def ticket_system(self, ctx: discord.ApplicationContext) -> None:
        """ Initializes the ticket system. """
        select_menu = TicketSelect(bot=self.bot, logger=self.logger)
        await ctx.respond("\u200bCreate a ticket:", view=select_menu)

def setup(bot) -> None:
    bot.add_cog(Ticket(bot))


class TicketSelect(discord.ui.View):
    """ Ticket select menu. """
    def __init__(self, bot, logger) -> None:
        super().__init__(timeout=None)
        self.bot: Ehrenbot = bot
        self.logger: Logger = logger

    options = [
        discord.SelectOption(label="Clan Join Request", emoji="👋", description="Request to join the clan",
                             value="Clan Join Request"),
        discord.SelectOption(label="Clan Support", emoji="👥", description="Request support for the clan",
                             value="Clan Support"),
        discord.SelectOption(label="User Report", emoji="👤", description="Report a user", value="User Report"),
        discord.SelectOption(label="Bug Report", emoji="🐛", description="Report a bug", value="Bug Report"),
        discord.SelectOption(label="Suggestion", emoji="📝", description="Request a suggestion", value="Suggestion"),
        discord.SelectOption(label="Other", emoji="❓", description="Other request", value="Other"),
    ]

    @discord.ui.select(
        placeholder="Create a ticket",
        min_values=1,
        max_values=1,
        options=options,
        custom_id="ticket_select")
    async def select_callback(self, select: discord.ui.Select, interaction: discord.Interaction) -> None:
        """ Callback for the select menu. """
        value = select.values[0]
        if value == "Clan Join Request":
            ticket_collection = self.bot.database["destiny_tickets"]
            ticket_id = ticket_collection.count_documents({}) + 1
            guild = self.bot.get_guild(782316238247559189)
            admin_channel: discord.TextChannel = discord.utils.get(guild.channels, name="📮｜admin-tickets")
            embed = discord.Embed(title="Clan Join Request", color=discord.Color.purple())
            embed.add_field(name="Id", value=ticket_id, inline=False)
            embed.add_field(name="User", value=interaction.user.mention)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            view = ClanRequestView(bot=self.bot, logger=self.logger)
            await admin_channel.send(embed=embed, view=view)
            admin_message_id = admin_channel.last_message_id
            ticket = {
                "title": "Clan Invite",
                "category": "Clan Join Request",
                "ticket_id": ticket_id,
                "status": "Open",
            }
            ticket_collection.insert_one({"ticket_id": ticket_id,
                                          "ticket": ticket,
                                          "admin_message_id": admin_message_id,
                                          "user_message_id": "",
                                          "discord_id": interaction.user.id})
            await interaction.response.send_message(
                "Request was created.\nPlease wait for a clan admin to respond to your request.",
                ephemeral=True, delete_after=10)
        else:
            await interaction.message.edit(content="", view=self)
            await interaction.response.send_modal(TicketModal(value, self.bot, self.logger))
        self.logger.info("User %s created a ticket with the category %s", interaction.user.name, value)


class TicketModal(discord.ui.Modal):
    """ Ticket modal. """
    def __init__(self, category, bot, logger) -> None:
        super().__init__(title=category)
        self.category: str = category
        self.bot: Ehrenbot = bot
        self.logger: Logger = logger
        self.add_item(discord.ui.InputText(label="Title", custom_id="title"))
        self.add_item(discord.ui.InputText(label="Description", placeholder="Enter description",
                                           custom_id="description", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction) -> None:
        """ Callback for the modal. """
        await interaction.response.defer()
        ticket_collection = self.bot.database["destiny_tickets"]
        ticket_id = ticket_collection.count_documents({}) + 1
        title = self.children[0].value
        category = self.category
        description = self.children[1].value
        ticket = {
            "title": title,
            "ticket_id": ticket_id,
            "status": "Open",
            "category": category,
            "description": description,
            "edit": "",
        }
        ticket_embed = create_ticket_embed(ticket, interaction.user)
        guild = self.bot.get_guild(782316238247559189)
        admin_channel: discord.TextChannel = discord.utils.get(guild.channels, name="📮｜admin-tickets")
        await admin_channel.send(embed=ticket_embed, view=TicketAdminView(self.bot, self.logger))
        last_admin_message_id = admin_channel.last_message_id
        await interaction.user.send(embed=ticket_embed, view=TicketUserView(self.bot, self.logger))
        last_user_message = await interaction.user.dm_channel.history(limit=1).next()
        last_user_message_id = last_user_message.id
        ticket_collection.insert_one({"ticket_id": ticket_id, "ticket": ticket, "admin_message_id": last_admin_message_id,
                                      "user_message_Id": last_user_message_id, "discord_id": interaction.user.id})
        await interaction.followup.send("Ticket was created. Visit your DM's to see your ticket.", ephemeral=True,
                                        delete_after=5)


class TicketUserView(discord.ui.View):
    """ User view for the ticket. """
    def __init__(self, bot, logger) -> None:
        super().__init__(timeout=None)
        self.bot: Ehrenbot = bot
        self.logger: Logger = logger

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.blurple, custom_id="edit")
    async def edit(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """ Callback for the edit button. """
        embed = interaction.message.embeds[0]
        ticket_id = int(embed.fields[0].value)
        ticket_collection = self.bot.database["destiny_tickets"]
        ticket: dict = ticket_collection.find_one({"ticket_id": int(ticket_id)})
        if not ticket:
            await interaction.response.send_message("Ticket not found", ephemeral=True, delete_after=5)
            self.logger.error("Ticket %d not found", ticket_id)
            return
        await interaction.response.send_modal(TicketEditModal(self.bot, self.logger, embed))

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="close")
    async def close(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """ Callback for the close button. """
        embed = interaction.message.embeds[0]
        await interaction.response.send_modal(TicketCloseModal(self.bot, self.logger, embed))


class TicketAdminView(discord.ui.View):
    """ Admin view for the ticket.

    Inherits from TicketUserView to add the in work button.
    """
    def __init__(self, bot, logger) -> None:
        super().__init__(timeout=None)
        self.bot: Ehrenbot = bot
        self.logger: Logger = logger
        for child in TicketUserView(bot, logger).children:
            self.children.append(child)

    @discord.ui.button(label="In Work", style=discord.ButtonStyle.green, custom_id="in_work")
    async def in_work(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """ Callback for the in work button. """
        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        ticket_id = int(embed.fields[0].value)

        if embed.color == discord.Color.gold():
            embed = await set_ticket_status(self.bot,  embed, "In Work")
            button.label = "Open"
            self.logger.info("User %s set Ticket %d to In Work", interaction.user, ticket_id)
        elif embed.color == discord.Color.green():
            embed = await set_ticket_status(self.bot,  embed, "Open")
            button.label = "In Work"
            self.logger.info("Ticket %d was set to Open", ticket_id)
        await sync_ticket(self.bot, self.logger, interaction, ticket_id, embed)
        await interaction.message.edit(content="", view=self)
        self.logger.info("Ticket %d was set to In Work", ticket_id)


class TicketEditModal(discord.ui.Modal):
    """ Modal for editing a ticket. """
    def __init__(self, bot, logger, embed) -> None:
        super().__init__(title="Edit Ticket")
        self.bot: Ehrenbot = bot
        self.logger: Logger = logger
        self.embed: discord.Embed = embed
        self.add_item(discord.ui.InputText(label="Edit", placeholder="Enter edit",
                                           custom_id="edit", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction) -> None:
        """ Callback for the modal. """
        await interaction.response.defer()
        ticket_id = int(self.embed.fields[0].value)
        # Edit embed
        edit: str = interaction.user.mention + "\n" + self.children[0].value
        # Check if embed has edit field
        if len(self.embed.fields) == 5:
            self.embed.add_field(name="Edit", value=edit, inline=False)
        else:
            edit_field = self.embed.fields[5]
            edit = edit_field.value + "\n" + edit
            self.embed.set_field_at(5, name="Edit", value=edit, inline=False)
        # sync ticket
        await sync_ticket(self.bot, self.logger, interaction, ticket_id, self.embed)
        await interaction.followup.send(f"Ticket {ticket_id} was edited.", ephemeral=True, delete_after=5)
        self.logger.info("Ticket %d was edited by %s", ticket_id, interaction.user)


class TicketCloseModal(discord.ui.Modal):
    """ Modal for closing a ticket. """
    def __init__(self, bot, logger, embed) -> None:
        super().__init__(title="Close Ticket")
        self.bot: Ehrenbot = bot
        self.logger: Logger = logger
        self.embed: discord.Embed = embed
        self.add_item(discord.ui.InputText(label="Solution", placeholder="Enter Solution here",
                                           custom_id="close", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction) -> None:
        """ Callback for the modal. """
        await interaction.response.defer()
        ticket_id = int(self.embed.fields[0].value)
        # Add solution to embed and set status to closed
        solution = self.children[0].value
        self.embed.add_field(name="Solution", value=solution, inline=False)
        embed = await set_ticket_status(self.bot,  self.embed, "Closed")
        # Get ticket from db
        ticket_collection = self.bot.database["destiny_tickets"]
        ticket: dict = ticket_collection.find_one({"ticket_id": ticket_id})
        if ticket is None:
            await interaction.followup.send("Ticket not found", ephemeral=True, delete_after=5)
            self.logger.error("Ticket %d not found", ticket_id)
            return
        admin_message_id: int = ticket["admin_message_id"]
        user_message_id: int = ticket["user_message_id"]
        # Remove views on messages
        guild = self.bot.get_guild(782316238247559189)
        admin_channel: discord.TextChannel = discord.utils.get(guild.channels, name="📮｜admin-tickets")
        admin_message = await admin_channel.fetch_message(admin_message_id)
        await admin_message.edit(content="", embed=embed, view=None)
        user_message = await interaction.user.fetch_message(user_message_id)
        await user_message.edit(content="", embed=embed, view=None)


class ClanRequestView(discord.ui.View):
    """ View for clan requests. """
    def __init__(self, bot, logger) -> None:
        super().__init__(timeout=None)
        self.bot: Ehrenbot = bot
        self.logger: Logger = logger

    @discord.ui.button(label="Invite", style=discord.ButtonStyle.blurple, custom_id="invite")
    async def invite(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """ Callback for the invite button. """
        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        ticket_id = int(embed.fields[0].value)
        # Get ticket from db
        ticket_collection = self.bot.database["destiny_tickets"]
        ticket: dict = ticket_collection.find_one({"ticket_id": ticket_id})
        if ticket is None:
            await interaction.followup.send("Ticket not found", ephemeral=True, delete_after=5)
            self.logger.warn("Ticket %d not found", ticket_id)
            return
        discord_id: int = ticket["discord_id"]
        # Get destiny credentials from db
        profile_collection = self.bot.database["members"]
        admin_profile = profile_collection.find_one({"discord_id": interaction.user.id})
        if admin_profile is None:
            await interaction.followup.send("Admin profile not found, please register.", ephemeral=True, delete_after=5)
            self.logger.warn("Admin profile not found")
            return
        user_profile = profile_collection.find_one({"discord_id": discord_id})
        if user_profile is None:
            await interaction.followup.send("Destiny profile not found", ephemeral=True, delete_after=5)
            self.logger.warn("Destiny profile for %d not found. Notifying user to register profile.", discord_id)
            user = self.bot.get_user(discord_id)
            await user.send("Your profile was not found in the database. Please register your profile with the command `/registration_bungie`")
            return
        admin_profile: dict = admin_profile["destiny_profile"]
        user_profile: dict = user_profile["destiny_profile"]
        token_collection = self.bot.database["destiny_tokens"]
        admin_token: dict = token_collection.find_one({"discord_id": interaction.user.id})["token"]
        admin_group_id: int = admin_profile["group_id"]

        user_membership_id: int = user_profile["destiny_membership_id"]
        user_membership_type: int = user_profile["membership_type"]

            # FIXME: This is not working
            # ! currently synchronous
        url = f"https://www.bungie.net/Platform/GroupV2/{admin_group_id}/Members/IndividualInvite/{user_membership_type}/{user_membership_id}/"
        payload = {
            "GroupApplicationRequest": {
                "message": f"{admin_profile['unique_name']} hat dich zu Code Ehre eingeladen.",
            }
        }
        headers = {
            "X-API-Key": BUNGIE_API_KEY,
            "Authorization": f"Bearer {admin_token['access_token']}"
        }
        response = requests.post(url=url, json=payload, headers=headers)
        # response = await self.bot.destiny_client.group_v2.IndividualGroupInvite(
        #     token=admin_token,
        #     group_id=admin_group_id,
        #     membership_type=user_membership_type,
        #     membership_id=user_membership_id,
        #     message=f"{admin_profile['unique_name']} hat dich zu Code Ehre eingeladen"
        # )
        if response is None:
            await interaction.followup.send("Invite failed", ephemeral=True, delete_after=5)
            self.logger.warn("Invite failed for %d", discord_id)
            return
        if response["ErrorCode"] == 1:
            await interaction.followup.send("User was invited", ephemeral=True, delete_after=5)
            user = self.bot.get_user(discord_id)
            await user.send("You were invited to the clan")
            self.logger.info("User %s was invited to Code Ehre", discord_id)
            ticket["ticket"]["status"] = "Closed"
            ticket_collection.update_one({"ticket_id": ticket_id}, {"$set": ticket})
            message_id = ticket["admin_message_id"]
            channel: discord.TextChannel = discord.utils.get(interaction.guild.channels, name="📮｜admin-tickets")
            message = await channel.fetch_message(message_id)
            await message.edit(content="", embed=embed, view=None)
        elif response["ErrorCode"] == 676:
            await interaction.followup.send("User is already in the clan", ephemeral=True, delete_after=5)
            self.logger.info("User %d is already in the clan", discord_id)
            ticket_collection.delete_one({"ticket_id": ticket_id})
            message_id: int = ticket["admin_message_id"]
            channel: discord.TextChannel = discord.utils.get(interaction.guild.channels, name="📮｜admin-tickets")
            message = await channel.fetch_message(message_id)
            await message.edit(embed=embed, view=None)
        elif response["ErrorCode"] == 12:
            await interaction.followup.send("You lack the privileges to invite someone to the clan!", ephemeral=True, delete_after=5)
        else:
            await interaction.followup.send("Something went wrong while inviting, check the logs.", ephemeral=True, delete_after=5)
            self.logger.error("Something went wrong while inviting user %d to Code Ehre\n%s", discord_id, response)
