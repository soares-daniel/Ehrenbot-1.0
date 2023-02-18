import os

from flask import Flask

from ehrenbot import Ehrenbot
from settings import DISCORD_BOT_TOKEN, SERVER_PORT

bot = Ehrenbot()

for filename in os.listdir("./ehrenbot/cogs"):
    if filename.endswith(".py") and filename != "__init__.py":
        bot.load_extension(f"ehrenbot.cogs.{filename[:-3]}")

app = Flask(__name__)

@app.route("/")
def hello():
    return "This is a flask web server hosted on Sparked Host!"

app.run(host='0.0.0.0', port=SERVER_PORT)
bot.run(DISCORD_BOT_TOKEN)
