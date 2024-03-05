import json
import logging
from datetime import datetime, time
from typing import Optional

import aiohttp
import discord
import pytz
from dateutil.parser import parse
from discord.ext import commands, tasks
from pydantic import BaseModel, ConfigDict

from ehrenbot.bot import Ehrenbot


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


class PogoEventResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    eventID: str
    name: str
    eventType: str
    heading: str
    link: str
    image: str
    start: str
    end: str
    extraData: Optional[dict] = {}  # TODO: Add model for extraData


class PogoEventEmbedData(PogoEventResponse):
    model_config = ConfigDict(extra="ignore")
    notes: list[str]
    color: int = 0x708090
    footer: str = "From Leekduck via ScrapedDuck"
    thumbnail: Optional[str] = None


class PogoEventDates(BaseModel):
    eventId: str
    start: datetime
    end: datetime


# list of every hour in a day
when = [time(hour=x, minute=0) for x in range(24)]


class PogoEventNotification(discord.Embed):
    def __init__(self, event: PogoEventEmbedData, event_dates: PogoEventDates):
        super().__init__(
            title=event.name,
            description=event.heading,
            url=event.link,
            color=event.color,
            timestamp=datetime.now(pytz.timezone("Europe/Berlin")),
        )

        self.set_footer(text=event.footer)
        self.set_image(url=event.image)
        if event.thumbnail:
            self.set_thumbnail(url=event.thumbnail)
        self.add_field(
            name="Start",
            value=event_dates.start.strftime("%d.%m.%Y %H:%M"),
            inline=True,
        )
        self.add_field(
            name="End",
            value=event_dates.end.strftime("%d.%m.%Y %H:%M"),
            inline=True,
        )
        if event.notes:
            self.add_field(
                name="Notes",
                value="\n".join(event.notes),
                inline=False,
            )


class PogoUpComingEvents(discord.Embed):
    def __init__(
        self, events: list[PogoEventEmbedData], event_dates: list[PogoEventDates]
    ):
        super().__init__(
            title="Upcoming Events",
            color=0x708090,
            url="https://leekduck.com/events/",
            timestamp=datetime.now(pytz.timezone("Europe/Berlin")),
        )
        self.set_thumbnail(
            url="https://assets.materialup.com/uploads/16628596-91da-45c6-8bd3-f514a2d5a58b/preview.jpg"
        )
        self.set_footer(text="From Leekduck via ScrapedDuck")
        for event in events:
            event_date = next(
                (date for date in event_dates if date.eventId == event.eventID), None
            )
            if event_date:
                self.add_field(
                    name=event.name,
                    value=f"{event_date.start.strftime('%d.%m.%Y %H:%M')} - {event_date.end.strftime('%d.%m.%Y %H:%M')} [Link]({event.link})",
                    inline=False,
                )


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
        berlin_tz = pytz.timezone("Europe/Berlin")
        self.event_dates = []
        for event in self.events:
            # Parse and convert to Berlin's timezone, then make naive
            event_start = parse(event.start).astimezone(berlin_tz).replace(tzinfo=None)
            event_end = parse(event.end).astimezone(berlin_tz).replace(tzinfo=None)
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
            active_event_embeds = [
                PogoEventNotification(active_events[i], self.event_dates[i])
                for i in range(len(active_events))
            ]
            for channel in channels:
                has_upcoming = False
                currently_in_channel = []
                async for message in channel.history(limit=100):
                    if message.embeds:
                        embed = message.embeds[0]
                        if embed.title == "Upcoming Events":
                            await message.edit(embed=upcoming_embed)
                            has_upcoming = True
                        else:
                            if embed.title not in [
                                event.name for event in active_events
                            ]:
                                await message.delete()
                                active_events.remove(
                                    event
                                    for event in active_events
                                    if event.name == embed.title
                                )
                            currently_in_channel.append(embed.title)
                if not has_upcoming:
                    await channel.send(embed=upcoming_embed)
                for event in active_event_embeds:
                    if event.title not in currently_in_channel:
                        await channel.send(embed=event)
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
