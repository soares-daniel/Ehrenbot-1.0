# pylint: disable=invalid-name
import logging
from datetime import time, timezone
from logging import handlers

from aiohttp import web

from destipy.destiny_client import DestinyClient
from discord import Activity, ActivityType, DiscordException, Intents
from discord.ext import commands
from discord.ext.i18n import Agent
from pymongo import MongoClient

from settings import (
    BUNGIE_API_KEY,
    BUNGIE_CLIENT_ID,
    BUNGIE_CLIENT_SECRET,
    DEBUG,
    MONGODB_PREFIX,
    MONGODB_HOST,
    MONGODB_OPTIONS,
    MONGODB_PASS,
    MONGODB_USER,
    REDIRECT_URI,
    WEB_SERVER_PORT,
)

class Ehrenbot(commands.Bot):
    """The Ehrenbot Discord bot."""

    def __init__(self) -> None:
        # Bot
        activity = Activity(type=ActivityType.watching, name="Ehrenserver")
        intents = Intents.all()
        super().__init__(activity=activity, command_prefix="!", intents=intents)
        # Logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        file_handler = handlers.TimedRotatingFileHandler(
            filename="logs/discord.log", when="midnight", backupCount=7
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)-8s - %(name)s - %(funcName)s - %(message)s"
        )
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
        conn = f"{MONGODB_PREFIX}://{MONGODB_USER}:{MONGODB_PASS}@{MONGODB_HOST}/?{MONGODB_OPTIONS}"
        print(conn)
        self.mongo_client = MongoClient(conn)
        self.database = (
            self.mongo_client["ehrenbot"] if not DEBUG else self.mongo_client["test"]
        )
        self.destiny_client = DestinyClient(
            BUNGIE_API_KEY, BUNGIE_CLIENT_ID, BUNGIE_CLIENT_SECRET, REDIRECT_URI
        )
        # Translator
        self.agent = Agent(translate_messages=True)

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
            self.destiny_invite_code = "tHQWSPuFVW"
        self.ADMIN_DISCORD_ID = 279725513323315200
        self.BUNGIE_BASE_URL = "https://www.bungie.net/"
        self.RESET_TIME = time(
            hour=17, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
        self.vendor_guild_id = 0
        self.mapped_states = {}  # state -> discord_id

    async def on_ready(self) -> None:
        print("------")
        print(self.user.name)
        print("From Ehrenmann to Ehrenmänner")
        print("------")
        print("Starting web server...")
        self.loop.create_task(self.web_server())

    async def on_application_command_error(
        self, ctx: commands.Context, error: DiscordException
    ) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.respond("This command is currently on cooldown!")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.respond(
                "You do not have the required permissions to run this command!"
            )
        else:
            raise error  # Here we raise other errors to ensure they aren't ignored

    async def handle_request(self, request: web.Request) -> web.Response:
        """Handle a request to the web server."""

        try:
            code = request.query["code"]
            state = request.query["state"]
            discord_id = self.mapped_states[state]
        except KeyError:
            return web.Response(text="Missing required query parameters.")

        # Fetch the token and save to the database
        try:
            token = await self.destiny_client.oauth.fetch_token(code, state)
        except Exception as e:
            print(f"Failed to fetch token: {e}")
            return web.Response(text="Failed to fetch token.")

        #  TODO: FIX fetch_token to raise exception if no token

        if token is None:
            return web.Response(text="Failed to fetch token.")

        entry = {
            "discord_id": discord_id,
            "membership_id": token["membership_id"],
            "token": token,
        }
        self.database["destiny_tokens"].insert_one(entry)

        # Remove state form mapped_states
        del self.mapped_states[state]

        # Serve HTML with JavaScript to close the tab
        html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <script type="text/javascript">
                    function closeWindow() {
                        window.close();
                    }
                    setTimeout(closeWindow, 1000);
                </script>
            </head>
            <body>
                <p>Token registered, you can go back to Discord.</p>
            </body>
            </html>
        """

        return web.Response(content_type="text/html", text=html_content)

    async def web_server(self) -> None:
        """Start the web server."""
        app = web.Application()
        app.router.add_get('/', self.handle_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', WEB_SERVER_PORT)
        await site.start()
        print(f"Web server started on port {WEB_SERVER_PORT}.")
