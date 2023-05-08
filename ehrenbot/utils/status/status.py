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
