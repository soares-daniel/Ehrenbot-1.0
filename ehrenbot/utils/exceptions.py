class NoBungieResponse(Exception):
    """Raised when the Bungie API does not respond"""

    def __init__(self, message: str = "No response from Bungie API"):
        self.message = message
        super().__init__(self.message)


class BungieMaintenance(Exception):
    """Raised when the Bungie API is in maintenance mode"""

    def __init__(self, message: str = "Bungie API is in maintenance mode"):
        self.message = message
        super().__init__(self.message)


class DestinyVendorNotFound(Exception):
    """Raised when the Destiny vendor is not found"""

    def __init__(self, message: str = "Vendor not found"):
        self.message = message
        super().__init__(self.message)


class BungieAPIError(Exception):
    """General Bungie API error"""

    def __init__(self, message: str = "Bungie API returned an error"):
        self.message = message
        super().__init__(self.message)


class TicketNotFound(Exception):
    """Raised when the ticket is not found"""

    def __init__(self, message: str = "Ticket not found"):
        self.message = message
        super().__init__(self.message)


class ProfileNotFound(Exception):
    """Raised when the profile is not found"""

    def __init__(
        self, message: str = "Profile not found. ErrorCode: ", error_status: str = ""
    ):
        self.message = message + error_status
        super().__init__(self.message)


class GroupNotFound(Exception):
    """Raised when the group/clan is not found"""

    def __init__(
        self, message: str = "Group not found. ErrorCode: ", error_status: str = ""
    ):
        self.message = message + error_status
        super().__init__(self.message)


class NoAPIResponse(Exception):
    """Raised when the API does not respond"""

    def __init__(self, message: str = "No response from API"):
        self.message = message
        super().__init__(self.message)


class MembershipDataNotFound(Exception):
    """Raised when the membership data is not found"""

    def __init__(
        self,
        message: str = "Membership data not found. ErrorCode: ",
        error_status: str = "",
    ):
        self.message = message + error_status
        super().__init__(self.message)
