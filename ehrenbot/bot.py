# pylint: disable=invalid-name
import logging
from datetime import time, timezone
from logging import handlers

from destipy.destiny_client import DestinyClient
from discord import Activity, ActivityType, DiscordException, Intents
from discord.ext import commands
from discord.ext.i18n import Agent
from pymongo import MongoClient

from settings import (BUNGIE_API_KEY, BUNGIE_CLIENT_ID, BUNGIE_CLIENT_SECRET,
                      DEBUG, MONGODB_HOST, MONGODB_OPTIONS, MONGODB_PASS,
                      MONGODB_USER, REDIRECT_URI)


class Ehrenbot(commands.Bot):
    """The Ehrenbot Discord bot."""
    def __init__(self) -> None:
        # Bot
        activity = Activity(type=ActivityType.competing, name="Bug fixing")
        intents = Intents.all()
        super().__init__(activity=activity, command_prefix="!",
                         intents=intents)
        # Logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        file_handler = handlers.TimedRotatingFileHandler(
            filename="logs/discord.log",
            when="midnight",
            backupCount=7
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(name)s - %(funcName)s - %(message)s')
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.ERROR)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

        self.file_handler = file_handler
        self.stream_handler = stream_handler
        self.logger = logger
        # MongoDB
        conn = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASS}@{MONGODB_HOST}/?{MONGODB_OPTIONS}"
        self.mongo_client = MongoClient(conn)
        self.database = self.mongo_client["ehrenbot"] if not DEBUG else self.mongo_client["test"]
        self.destiny_client = DestinyClient(BUNGIE_API_KEY, BUNGIE_CLIENT_ID,
                                            BUNGIE_CLIENT_SECRET, REDIRECT_URI)
        # Translator
        self.agent = Agent(translate_all=True)

        # Misc
        self.DEBUG = DEBUG
        self.MAIN_GUILD_ID = 782316238247559189
        self.DEBUG_GUILD_ID = 992420245241352232
        if DEBUG:
            self.GUILD_ID = self.DEBUG_GUILD_ID
            self.destiny_invite_code = "UzaGXQ5twM"
            self.lux_invite_code = "QhGzKJSs"
        else:
            self.GUILD_ID = self.MAIN_GUILD_ID
            self.destiny_invite_code = "YJmhrdcHnX"
            self.lux_invite_code = "dzwf8PN2xs"
        self.ADMIN_DISCORD_ID = 279725513323315200
        self.BUNGIE_BASE_URL = "https://www.bungie.net/"
        self.RESET_TIME = time(hour=17, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        self.vendor_guild_id = 0

    async def on_ready(self) -> None:
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("------")

    async def on_application_command_error(self, ctx: commands.Context, error: DiscordException) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.respond("This command is currently on cooldown!")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.respond("You do not have the required permissions to run this command!")
        else:
            raise error  # Here we raise other errors to ensure they aren't ignored
