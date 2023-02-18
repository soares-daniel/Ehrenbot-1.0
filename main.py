import os
import threading

from dashboard.app import app
from ehrenbot import Ehrenbot
from settings import DISCORD_BOT_TOKEN

bot = Ehrenbot()

for filename in os.listdir("./ehrenbot/cogs"):
    if filename.endswith(".py") and filename != "__init__.py":
        bot.load_extension(f"ehrenbot.cogs.{filename[:-3]}")

bot.run(DISCORD_BOT_TOKEN)


def run_app():
    app.run(debug=True)


thread = threading.Thread(target=run_app)
thread.start()
os.system("python main.py")
