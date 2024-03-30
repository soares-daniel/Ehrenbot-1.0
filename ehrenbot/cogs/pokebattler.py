import logging
import aiohttp
import discord
from datetime import datetime, time

from bs4 import BeautifulSoup

from discord.ext import commands, tasks

from ehrenbot.types import PokeBattlerArticle
from ehrenbot.embeds.pokebattler_article import PokeBattlerArticleEmbed

every_hour = [time(hour=x, minute=0) for x in range(24)]


class PokeBattler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.bot.file_handler)
        self.logger.addHandler(self.bot.stream_handler)

        self.articles: list[PokeBattlerArticle] = []
        self.do_fetch_articles.start()

    def cog_unload(self):
        self.do_fetch_articles.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.fetch_articles()

    @tasks.loop(time=every_hour)
    async def do_fetch_articles(self):
        await self.fetch_articles()

    @do_fetch_articles.before_loop
    async def before_fetch_events(self):
        await self.bot.wait_until_ready()

    async def fetch_articles(self):
        self.logger.info("Fetching PokeBattler articles")
        today = datetime.now()
        month = today.month if today.month > 9 else f"0{today.month}"
        day = today.day if today.day > 9 else f"0{today.day}"
        url = f"https://articles.pokebattler.com/{today.year}/{month}/{day}/"
        self.articles = []
        async with aiohttp.ClientSession() as session:
            response = await session.get(url)
            if response.status == 200:
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                articles = soup.find_all('article')  # Adjust based on actual site structure

                for article in articles:
                    title = article.find('h2').text.strip() if article.find('h2') else 'No title'
                    image = article.find('img')['src'] if article.find('img') else 'No image'
                    article_url = article.find('a')['href'] if article.find('a') else 'No URL'
                    self.articles.append(PokeBattlerArticle(title=title, url=article_url, image=image, published=datetime.timestamp(today)))
            elif response.status == 404:
                self.logger.error(f"No articles found for {today.year}/{month}/{day}")
            else:
                self.logger.error(f"Failed to fetch PokeBattler articles: {response.status}")

        await self.send_articles()

    async def send_articles(self):
        channel_entries = self.bot.database["channels"].find({"type": "pokebattler_articles"})
        channels = [self.bot.get_channel(entry["channel_id"]) for entry in channel_entries]
        for channel in channels:
            article_urls_in_channel = []
            async for message in channel.history(limit=100):
                if message.embeds:
                    embed = message.embeds[0]
                    article_urls_in_channel.append(embed.url)
            for article in self.articles:
                if article.url not in article_urls_in_channel:
                    await channel.send(embed=PokeBattlerArticleEmbed(article))



    @commands.slash_command(
        name="pokebattler_articles",
        description="Commands to add and remove Pokémon GO event notifications in Channel.",
    )
    @commands.guild_only()
    async def pogo_events(self, ctx: discord.ApplicationContext):
        # Check if channel is already in db and if not, add it else remove it
        if self.bot.database["channels"].find_one(
            ({"channel_id": ctx.channel.id, "type": "pokebattler_articles"})
        ):
            self.bot.database["channels"].delete_one(
                {"channel_id": ctx.channel.id, "type": "pokebattler_articles"}
            )
            await ctx.respond(
                "Channel removed from notification list.",
                ephemeral=True,
                delete_after=10,
            )
        else:
            self.bot.database["channels"].insert_one(
                {
                    "channel_id": ctx.channel.id,
                    "guild_id": ctx.guild.id,
                    "type": "pokebattler_articles",
                }
            )
            await ctx.respond(
                "Channel added to notifications list.", ephemeral=True, delete_after=10
            )

def setup(bot):
    bot.add_cog(PokeBattler(bot))
