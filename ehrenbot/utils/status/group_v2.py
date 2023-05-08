from ehrenbot import Ehrenbot

from .status import update_status


async def check_group_v2_status(bot: Ehrenbot, group_id: int) -> bool:
    """Check if the GroupV2 endpoints are online."""
    group_v2 = bot.destiny_client.group_v2
    status = {
        "Status": "**ERROR**",
        "Category": "GroupV2",
        "Used Endpoint": "`GetGroup`",
    }
    response = await group_v2.GetGroup(group_id=group_id)
    return update_status(response, status)
