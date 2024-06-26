import json
import logging
from datetime import datetime, time

import aiohttp
import discord
import pytz
from dateutil.parser import parse
from discord.ext import commands, tasks

from ehrenbot.bot import Ehrenbot
from ehrenbot.types import PogoEventDates, PogoEventEmbedData, PogoEventResponse
from ehrenbot.embeds.pogo_upcoming_events import PogoUpComingEvents

event_colors = {
    "community-day": 0xFFD700,
    "event": 0x708090,
    "live-event": 0xFF4500,
    "pokemon-go-fest": 0xFF8C00,
    "global-challenge": 0x32CD32,
    "safari-zone": 0xFF69B4,
    "ticketed-event": 0xBA55D3,
    "location-specific": 0x20B2AA,
    "bonus-hour": 0x3CB371,
    "pokemon-spotlight-hour": 0xFFA07A,
    "potential-ultra-unlock": 0xFF6347,
    "update": 0x4682B4,
    "season": 0x98FB98,
    "pokemon-go-tour": 0xDDA0DD,
    "research": 0x8A2BE2,
    "timed-research": 0x7B68EE,
    "limited-research": 0x6A5ACD,
    "research-breakthrough": 0x9400D3,
    "special-research": 0x9932CC,
    "raid-day": 0xFF0000,
    "raid-battles": 0xDC143C,
    "raid-hour": 0xC71585,
    "raid-weekend": 0xDB7093,
    "go-battle-league": 0xB22222,
    "go-rocket-takeover": 0x800080,
    "team-go-rocket": 0x808000,
    "giovanni-special-research": 0x4B0082,
    "elite-raids": 0x000000,
}

# list of every hour in a day
when = [time(hour=x, minute=0) for x in range(24)]

class Pokemon(commands.Cog):
    def __init__(self, bot):
        self.bot: Ehrenbot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

        self.events = {}
        self.event_dates: list[PogoEventDates] = []
        self.notes = {
            "raid-day": [
                "Additional daily passes can only be obtained during the Raid Day hours for the specific Pokemon."
            ]
        }
        self.do_fetch_events.start()

    def cog_unload(self):
        self.do_fetch_events.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.fetch_events()

    async def gather_event_dates(self):
        self.event_dates = []
        for event in self.events:
            # Directly parse the start and end times without converting them to a specific timezone
            event_start = parse(event.start)
            event_end = parse(event.end)

            # Ensure all datetime objects are offset-naive by removing timezone information
            event_start = (
                event_start.replace(tzinfo=None)
                if event_start.tzinfo is not None
                else event_start
            )
            event_end = (
                event_end.replace(tzinfo=None)
                if event_end.tzinfo is not None
                else event_end
            )

            self.event_dates.append(
                PogoEventDates(eventId=event.eventID, start=event_start, end=event_end)
            )
        self.event_dates.sort(key=lambda x: x.start)

    @tasks.loop(time=when)
    async def do_fetch_events(self):
        await self.fetch_events()

    @do_fetch_events.before_loop
    async def before_fetch_events(self):
        await self.bot.wait_until_ready()

    async def fetch_events(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://raw.githubusercontent.com/bigfoott/ScrapedDuck/data/events.min.json"
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    try:
                        data = json.loads(text)  # Parse text as JSON
                        events = [PogoEventResponse(**event) for event in data]
                        self.events = [
                            PogoEventEmbedData(
                                **event.dict(),
                                notes=self.notes.get(event.eventType, []),
                                color=event_colors.get(event.eventType, 0x708090),
                            )
                            for event in events
                        ]
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse JSON: {e}")
                else:
                    self.logger.error(
                        f"Failed to fetch Pokemon GO events with status: {response.status}"
                    )
        await self.gather_event_dates()
        await self.event_notifications()

    async def event_notifications(self):
        current_time = datetime.now(pytz.timezone("Europe/Berlin")).replace(tzinfo=None)
        channel_entries = self.bot.database["channels"].find({"type": "pogo_events"})
        channels = [
            self.bot.get_channel(entry["channel_id"]) for entry in channel_entries
        ]
        active_events: list[PogoEventEmbedData] = []
        upcoming_events: list[PogoEventEmbedData] = []
        try:
            for event_date in self.event_dates:  # Sorted
                event = next(
                    (
                        event
                        for event in self.events
                        if event.eventID == event_date.eventId
                    ),
                    None,
                )
                if event is None:
                    continue
                if event_date.start > current_time:
                    if len(upcoming_events) < 25:
                        upcoming_events.append(event)
                elif event_date.start <= current_time < event_date.end:
                    active_events.append(event)
                elif current_time >= event_date.end:
                    pass
            upcoming_embed = PogoUpComingEvents(upcoming_events, self.event_dates)
            for channel in channels:
                has_upcoming = False
                async for message in channel.history(limit=100):
                    if message.embeds:
                        embed = message.embeds[0]
                        if embed.title == "Upcoming Events":
                            await message.edit(embed=upcoming_embed)
                            has_upcoming = True
                        else:
                            continue
                if not has_upcoming:
                    await channel.send(embed=upcoming_embed)
        except Exception as e:
            self.logger.error(f"Failed to send event notifications: {e}")

    @commands.slash_command(
        name="pogo_events",
        description="Commands to add and remove Pokémon GO event notifications in Channel.",
    )
    @commands.guild_only()
    async def pogo_events(self, ctx: discord.ApplicationContext):
        # Check if channel is already in db and if not, add it else remove it
        if self.bot.database["channels"].find_one(
            ({"channel_id": ctx.channel.id, "type": "pogo_events"})
        ):
            self.bot.database["channels"].delete_one(
                {"channel_id": ctx.channel.id, "type": "pogo_events"}
            )
            await ctx.respond(
                "Channel removed from event notifications.",
                ephemeral=True,
                delete_after=10,
            )
        else:
            self.bot.database["channels"].insert_one(
                {
                    "channel_id": ctx.channel.id,
                    "guild_id": ctx.guild.id,
                    "type": "pogo_events",
                }
            )
            await ctx.respond(
                "Channel added to event notifications.", ephemeral=True, delete_after=10
            )


def setup(bot):
    bot.add_cog(Pokemon(bot))
