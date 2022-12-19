import asyncio
import logging

from discord import ApplicationContext, Message
from discord.ext import commands, tasks

from ehrenbot import Ehrenbot
from ehrenbot.utils.utils_registration import setup_profile, update_profile


class Registration(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)
        self.update_tokens.start()

    def cog_unload(self) -> None:
        self.update_tokens.cancel()

    @commands.slash_command(name="register", description="Link your Bungie account with your Discord account.")
    @commands.guild_only()
    async def register(self, ctx: ApplicationContext) -> None:
        token_collection = self.bot.database["tokens"]
        if token_collection.find_one({"discord_id": ctx.author.id}):
            await ctx.respond("You are already registered.", ephemeral=True, delete_after=10)
            return
        await ctx.respond("Check your DMs", ephemeral=True, delete_after=10)
        await ctx.author.send("To register your Bungie account with your Discord account, please visit the following link:")
        oauth = self.bot.destiny_client.oauth
        url = await oauth.gen_auth_link()
        await ctx.author.send(url)

        try:
            # Wait for the user to respond with the url
            msg: Message = await self.bot.wait_for("message",
                                          check=lambda m: m.author == ctx.author
                                          and m.channel == ctx.author.dm_channel
                                          and m.content.startswith("https://bungie.sedam.me"),
                                          timeout=300)
        except asyncio.TimeoutError:
            await ctx.author.send("You took too long to respond. Please try again.")
            return
        else:
            # Store the token in the database, setup profile
            token = await oauth.fetch_token(msg.content)
            entry = {
                "discord_id": ctx.author.id,
                "membership_id": token["membership_id"],
                "token": token,
            }
            token_collection.insert_one(entry)

            if await setup_profile(self.bot, ctx.author.id, token["membership_id"]):
                if await update_profile(self.bot, ctx.author.id):
                    await ctx.author.send("Your Bungie account has been successfully linked to your Discord account!", delete_after=10)
                else:
                    await ctx.author.send("Something went wrong while updating your profile. Please contact the admin.", delete_after=10)
            else:
                await ctx.author.send("Something went wrong while setting up your profile. Please contact the admin.", delete_after=10)

    @tasks.loop(hours=1)
    async def update_tokens(self) -> None:
        token_collection = self.bot.database["destiny_tokens"]
        oauth = self.bot.destiny_client.oauth
        for token in token_collection.find():
            new_token = await oauth.refresh_token(token["token"])
            if new_token:
                token_collection.update_one({"discord_id": token["discord_id"]}, {"$set": {"token": new_token}})

    @update_tokens.before_loop
    async def before_update_tokens(self) -> None:
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Registration(bot))
