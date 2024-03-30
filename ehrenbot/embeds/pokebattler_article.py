import discord
from datetime import datetime
import pytz

from ehrenbot.types import PokeBattlerArticle

class PokeBattlerArticleEmbed(discord.Embed):
    def __init__(self, article: PokeBattlerArticle):
        super().__init__(
            title=article.title,
            color=0x708090,
            url=article.url,
            timestamp=datetime.fromtimestamp(article.published, pytz.timezone("Europe/Berlin")),
        )
        self.set_image(url=article.image)
        self.set_footer(text="From PokeBattler via Ehrenbot")
        self.set_author(name="PokeBattler", icon_url="https://static.pokebattler.com/images/og_home.png")
