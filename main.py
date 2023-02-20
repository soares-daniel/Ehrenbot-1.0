import os
from ehrenbot import Ehrenbot
from settings import DISCORD_BOT_TOKEN

bot = Ehrenbot()

for filename in os.listdir("./ehrenbot/cogs"):
    if filename.endswith(".py") and filename != "__init__.py":
        bot.load_extension(f"ehrenbot.cogs.{filename[:-3]}")

bot.run(DISCORD_BOT_TOKEN)
