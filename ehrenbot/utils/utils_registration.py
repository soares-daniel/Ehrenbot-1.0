import json

from ehrenbot import Ehrenbot


async def setup_profile(bot: Ehrenbot, discord_id: int, membership_id: int) -> None:
    profile_collection = bot.database["destiny_profiles"]
    with open("ehrenbot/data/guardian_template.json", "r", encoding="utf-8") as file:
        guardian_template = json.load(file)
    profile_collection.insert_one({"discord_id": discord_id, "profile": guardian_template, "membership_id": membership_id})

async def update_profile(bot: Ehrenbot, discord_id: int) -> bool:
    token_collection = bot.database["destiny_tokens"]
    profile_collection = bot.database["destiny_profiles"]
    token = token_collection.find_one({"discord_id": discord_id})["token"]
    if not token:
        bot.logger.error("Could not find token for %d", discord_id)
        return False
    profile = profile_collection.find_one({"discord_id": discord_id})["profile"]
    if not profile:
        bot.logger.error("Could not find profile for %d, creating new profile...", discord_id)
        await setup_profile(bot, discord_id, token["membership_id"])

    try:
        user_endpoints = bot.destiny_client.user
        response = await user_endpoints.GetMembershipDataForCurrentUser(token=token)
        if response is None:
            raise Exception("Could not get membership data for current user.")
        if response["ErrorCode"] != 1:
            raise Exception(f"Could not get membership data for current user: {response['ErrorStatus']}")
        data = response["Response"]
        profile["destiny_membership_id"] = data["destinyMemberships"][0]["membershipId"]
        profile["membership_type"] = data["destinyMemberships"][0]["membershipType"]
        user_data = data["bungieNetUser"]
        profile["membership_id"] = token["membership_id"]
        profile["display_name"] = user_data.get("displayName", "")
        profile["unique_name"] = user_data.get("uniqueName", "")
        profile["locale"] = user_data.get("locale", "")
        profile["profile_picture_path"] = user_data.get("profilePicturePath", "")
        profile["is_deleted"] = user_data.get("isDeleted", True)
        profile["first_access"] = user_data.get("firstAccess", "")
        profile["last_update"] = user_data.get("lastUpdate", "")
        profile["egs_display_name"] = user_data.get("egsDisplayName", "")
        profile["psn_display_name"] = user_data.get("psnDisplayName", "")
        profile["xbox_display_name"] = user_data.get("xboxDisplayName", "")
        profile["blizzard_display_name"] = user_data.get("blizzardDisplayName", "")
        profile["steam_display_name"] = user_data.get("steamDisplayName", "")
        profile["stadia_display_name"] = user_data.get("stadiaDisplayName", "")
        profile["twitch_display_name"] = user_data.get("twitchDisplayName", "")
        profile["cached_bungie_global_display_name"] = user_data.get("cachedBungieGlobalDisplayName", "")
        profile["cached_bungie_global_display_name_code"] = user_data.get("cachedBungieGlobalDisplayNameCode", 0)

        destiny2_endpoints = bot.destiny_client.destiny2
        response = await destiny2_endpoints.GetProfile(destiny_membership_id=profile["destiny_membership_id"],
                                                    membership_type=profile["membership_type"],
                                                    components=[100])
        if response is None:
            raise Exception("Could not get profile.")
        if response["ErrorCode"] != 1:
            raise Exception(f"Could not get profile: {response['ErrorStatus']}")
        data = response["Response"]["profile"]["data"]
        profile["cross_save_override"] = data["userInfo"].get("crossSaveOverride", 0)
        profile["applicable_membership_types"] = data["userInfo"].get("applicableMembershipTypes", [])
        profile["is_public"] = data["userInfo"].get("isPublic", False)
        profile["date_last_played"] = data["dateLastPlayed", ""]
        profile["character_ids"] = data["characterIds", []]

        group_v2_endpoints = bot.destiny_client.group_v2
        response = await group_v2_endpoints.GetGroupsForMember(membership_type=profile["membership_type"],
                                                            destiny_membership_id=profile["destiny_membership_id"])
        if response is None:
            raise Exception("Could not get groups for member.")
        if response["ErrorCode"] != 1:
            raise Exception(f"Could not get groups for member: {response['ErrorStatus']}")
        data = response["Response"].get("results")
        if data:
            profile["group_id"] = data[0]["member"]["groupId"]

        profile_collection.update_one({"discord_id": discord_id}, {"$set": {"profile": profile}})
        bungie_name = profile["unique_name"]
        bot.logger.info("%s has been updated successfully!", bungie_name)
        return True

    except Exception as ex:
        bot.logger.error("Could not update profile for %d: %s", discord_id, ex)
        return False
