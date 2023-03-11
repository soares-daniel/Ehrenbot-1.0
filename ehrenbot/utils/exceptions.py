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
