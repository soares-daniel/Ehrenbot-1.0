from ehrenbot import Ehrenbot

from .status import update_status


async def check_api_status(bot: Ehrenbot) -> bool:
    """Check if the Bungie API is online."""
    destiny2 = bot.destiny_client.destiny2
    status = {
        "Status": "**ERROR**",
        "Category": "API",
        "Used Endpoint": "`GetDestinyManifest`",
    }
    response = await destiny2.GetDestinyManifest()
    return update_status(response, status)
