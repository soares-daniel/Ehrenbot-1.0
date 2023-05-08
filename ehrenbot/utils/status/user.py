from ehrenbot import Ehrenbot

from .status import update_status


async def check_user_status(
    bot: Ehrenbot, destiny_membership_id: int, membership_type: int
) -> bool:
    """Check if User endpoints are online."""
    destiny2 = bot.destiny_client.destiny2
    status = {
        "Status": "**ERROR**",
        "Category": "User",
        "Used Endpoint": "`GetProfile`",
    }
    response = await destiny2.GetProfile(
        destiny_membership_id=destiny_membership_id,
        membership_type=membership_type,
        components=[100],
    )
    return update_status(response, status)
