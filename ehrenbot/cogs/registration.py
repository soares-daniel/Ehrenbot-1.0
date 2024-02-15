import asyncio
import csv
import logging
from urllib.parse import parse_qs, urlparse
from datetime import time, timezone

import discord
from discord.ext import commands, tasks

from ehrenbot import Ehrenbot
from ehrenbot.utils.exceptions import BungieAPIError
from ehrenbot.utils.registration import (
    check_profile_endpoints,
    setup_profile,
    update_profile,
)


class Registration(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)
        self.update_tokens.start()
        self.update_profiles.start()

    def cog_unload(self) -> None:
        self.update_tokens.cancel()
        self.update_profiles.cancel()

    @commands.slash_command(
        name="register",
        description="Link your Bungie account with your Discord account.",
    )
    @commands.guild_only()
    async def send_registration(self, ctx: discord.ApplicationContext):
        """Link your Bungie account with your Discord account"""
        token_collection = self.bot.database["destiny_tokens"]
        try:
            await check_profile_endpoints(self.bot)
        except BungieAPIError:
            await ctx.respond(
                "The Bungie API is currently unavailable. Please try again later.",
                ephemeral=True,
                delete_after=10,
            )
            return
        await ctx.respond("Check your DMs", ephemeral=True, delete_after=10)
        await ctx.author.send(
            "To register your Bungie account with your Discord account, please visit the following link:"
        )
        oauth = self.bot.destiny_client.oauth
        url = await oauth.gen_auth_link()
        parts = urlparse(url)
        query_dict = parse_qs(parts.query)
        state = query_dict["state"][0]
        # store the state in the database via update_one
        self.bot.database["states"].update_one(
            {"discord_id": ctx.author.id}, {"$set": {"state": state}}, upsert=True
        )
        await ctx.author.send(url)

        # Check during 300 seconds if the token has been stored in the database
        token = token_collection.find_one({"discord_id": ctx.author.id})
        if token is None:
            for _ in range(300):
                if token is None:
                    await asyncio.sleep(1)
                    token = token_collection.find_one({"discord_id": ctx.author.id})
                else:
                    break

        if token is None:
            await ctx.author.send(
                "The token could not be found in the database. Please try again."
            )
            return

        if await setup_profile(self.bot, ctx.author.id, token["membership_id"]):
            if await update_profile(self.bot, ctx.author.id):
                await ctx.author.send(
                    "Your Bungie account has been successfully linked to your Discord account!",
                    delete_after=10,
                )
                # Give the user the "registered" role
                role = discord.utils.get(ctx.guild.roles, name="Registered")
                if not role:
                    await ctx.guild.create_role(name="Registered")
                await ctx.author.add_roles(role)
                # Update memberhall
                members_collection = self.bot.database["members"]
                member = members_collection.find_one({"discord_id": ctx.author.id})
                channel = ctx.guild.get_channel(member["channel_id"])
                message = await channel.fetch_message(member["message_id"])
                embed = message.embeds[0]
                embed.add_field(
                    name="Bungie.Net",
                    value=member["destiny_profile"]["unique_name"],
                    inline=False,
                )
                embed.color = discord.Color.green()
                await message.edit(content="", embed=embed)
                # Insert member to shader notifications
                with open("data/notify-shaders.csv", "a", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerow([ctx.author.id])
            else:
                await ctx.author.send(
                    "Something went wrong while updating your profile. Please contact the admin.",
                    delete_after=10,
                )
        else:
            await ctx.author.send(
                "Something went wrong while setting up your profile. Please contact the admin.",
                delete_after=10,
            )

    @tasks.loop(hours=1)
    async def update_tokens(self):
        self.logger.debug("Updating tokens...")
        token_collection = self.bot.database["destiny_tokens"]
        oauth = self.bot.destiny_client.oauth
        for token in token_collection.find():
            new_token = await oauth.refresh_token(token["token"])
            if new_token.get("membership_id") == token["membership_id"]:
                token_collection.update_one(
                    {"discord_id": token["discord_id"]}, {"$set": {"token": new_token}}
                )
                self.logger.debug("Updated token for %s", token["discord_id"])
            else:
                self.logger.warning(
                    "Token for <membership_id> %s is invalid", token["membership_id"]
                )
        self.logger.info("Tokens updated.")

    @update_tokens.before_loop
    async def before_update_tokens(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=time(hour=3, tzinfo=timezone.utc))
    async def update_profiles(self):
        token_collection = self.bot.database["tokens"]
        for entry in token_collection.find():
            await update_profile(self.bot, entry["discord_id"])

    @update_profiles.before_loop
    async def before_update_profiles(self):
        await self.bot.wait_until_ready()


def setup(bot) -> None:
    bot.add_cog(Registration(bot))
