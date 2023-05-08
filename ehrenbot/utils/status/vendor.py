from ehrenbot import Ehrenbot

from .status import update_status


async def check_vendor_status(
    bot: Ehrenbot,
    destiny_membership_id: int,
    membership_type: int,
    character_id: int,
    token: dict,
) -> bool:
    """Check if the Vendor endpoints are online."""
    destiny2 = bot.destiny_client.destiny2
    status = {
        "Status": "**ERROR**",
        "Category": "Vendor",
        "Used Endpoint": "`GetVendors`",
    }
    response = await destiny2.GetVendors(
        token=token,
        character_id=character_id,
        destiny_membership_id=destiny_membership_id,
        membership_type=membership_type,
        components=[400],
    )
    return update_status(response, status)
