from ehrenbot import Ehrenbot

def update_status(response: dict, status: dict) -> dict:
    """Update the status based on the response."""
    if response is None:
        status["Status"] = "🔴 **Offline**"
        return status
    if response.get("ErrorCode") == 5:
        status["Status"] = "🟡 **Maintenance**"
    elif response.get("ErrorCode") == 1:
        status["Status"] = "🟢 **Online**"
    return status

async def check_user_status(bot: Ehrenbot, destiny_membership_id: int, membership_type: int) -> bool:
    """Check if User endpoints are online."""
    destiny2 = bot.destiny_client.destiny2
    status = {"Status": "**ERROR**", "Category": "User", "Used Endpoint": "`GetProfile`"}
    response = await destiny2.GetProfile(destiny_membership_id=destiny_membership_id,
                                         membership_type=membership_type,
                                         components=[100])
    return update_status(response, status)

async def check_api_status(bot: Ehrenbot) -> bool:
    """Check if the Bungie API is online."""
    destiny2 = bot.destiny_client.destiny2
    status = {"Status": "**ERROR**", "Category": "API", "Used Endpoint": "`GetDestinyManifest`"}
    response = await destiny2.GetDestinyManifest()
    return update_status(response, status)

async def check_vendor_status(bot: Ehrenbot, destiny_membership_id: int, membership_type: int, character_id: int, token: dict) -> bool:
    """Check if the Vendor endpoints are online."""
    destiny2 = bot.destiny_client.destiny2
    status = {"Status": "**ERROR**", "Category": "Vendor", "Used Endpoint": "`GetVendors`"}
    response = await destiny2.GetVendors(token=token,
                                         character_id=character_id,
                                         destiny_membership_id=destiny_membership_id,
                                         membership_type=membership_type,
                                         components=[400])
    return update_status(response, status)

async def check_group_v2_status(bot: Ehrenbot, group_id: int) -> bool:
    """Check if the GroupV2 endpoints are online."""
    group_v2 = bot.destiny_client.group_v2
    status = {"Status": "**ERROR**", "Category": "GroupV2", "Used Endpoint": "`GetGroup`"}
    response = await group_v2.GetGroup(group_id=group_id)
    return update_status(response, status)
