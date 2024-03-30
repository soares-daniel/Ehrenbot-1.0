from datetime import datetime
import pytz

import discord

from ehrenbot.types import PogoEventEmbedData, PogoEventDates


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