
class NoBungieResponse(Exception):
    def __init__(self, message: str = "No response from Bungie API"):
        self.message = message
        super().__init__(self.message)

class BungieMaintenance(Exception):
    def __init__(self, message: str = "Bungie API is in maintenance mode"):
        self.message = message
        super().__init__(self.message)

class DestinyVendorNotFound(Exception):
    def __init__(self, message: str = "Vendor not found"):
        self.message = message
        super().__init__(self.message)

class BungieAPIError(Exception):
    def __init__(self, message: str = "Bungie API returned an error"):
        self.message = message
        super().__init__(self.message)
