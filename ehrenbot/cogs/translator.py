from typing import Optional

import discord
from discord.ext import commands
from discord.ext.i18n import Detector, Language

from ehrenbot import Ehrenbot


class Translator(commands.Cog, Detector):
    def __init__(self, bot: Ehrenbot) -> None:
        self.bot = bot

    @Detector.lang_getter
    async def get_lang(self, discord_id) -> Optional[Language]:
        """ Get the language of a user """
        language_collection = self.bot.database["languages"]
        entry = language_collection.find_one({"discord_id": discord_id})
        return Language.from_name(entry["language"]) if entry else None

    @commands.slash_command(name="lang")
    async def set_lang(self, ctx: discord.ApplicationContext, lang_code: str):
        """ Set the language of a user """
        language_collection = self.bot.database["languages"]
        lang = Language.from_code(lang_code)
        if lang is None:
            return await ctx.respond("Bad language code!", ephemeral=True, delete_after=10)
        if lang is Language.English:
            if language_collection.find_one({"discord_id": ctx.author.id}):
                language_collection.delete_one({"discord_id": ctx.author.id})
        else:
            language_collection.update_one({"discord_id": ctx.author.id}, {"$set": {"language": lang.name}}, upsert=True)

        await ctx.respond(f"I've set the language to `{lang.name.title()}` {lang.emoji}!", ephemeral=True, delete_after=10)


def setup(bot):
    bot.add_cog(Translator(bot))
