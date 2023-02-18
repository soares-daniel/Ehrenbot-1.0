import os
import threading

from dashboard.app import app
from ehrenbot import Ehrenbot
from settings import DISCORD_BOT_TOKEN, SERVER_PORT

bot = Ehrenbot()

for filename in os.listdir("./ehrenbot/cogs"):
    if filename.endswith(".py") and filename != "__init__.py":
        bot.load_extension(f"ehrenbot.cogs.{filename[:-3]}")

def run_app():
    app.run(host='0.0.0.0', port=SERVER_PORT)

web_thread = threading.Thread(target=run_app)
web_thread.start()

bot.run(DISCORD_BOT_TOKEN)
