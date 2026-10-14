import httpx
import logging

logger = logging.getLogger("search_assistant")

class CommandsService:
    def __init__(self):
        # Register command keywords/prefixes to their respective handler methods
        self.registry = {
            "temp home": self._handle_temp_home,
            "whois": self._handle_whois,  # Easily scalable for other command categories
        }

    async def process_command(self, query: str) -> str | None:
        """
        Checks if the sanitized query matches any registered command.
        Returns the formatted SMS string if matched, otherwise None.
        """
        normalized_query = query.strip().lower()

        for command_key, handler in self.registry.items():
            if normalized_query == command_key or normalized_query.startswith(command_key + " "):
                try:
                    return await handler(normalized_query)
                except Exception as e:
                    logger.error(f"Command execution error for '{normalized_query}': {e}")
                    return f"Error: Failed to execute command '{command_key}'."

        return None

    async def _handle_temp_home(self, query: str) -> str:
        """Fetches climate sensor readings from the ThingSpeak API and rounds floats to 2 decimal places."""
        channel_id = "3532509"  # Keep channel as a variable
        url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.json?results=1"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            feeds = data.get("feeds", [])
            if not feeds:
                return f"Error: No data available for channel {channel_id}"

            latest_feed = feeds[0]

            # Helper function safely converts values to float and rounds them to 2 decimal places
            def format_val(val):
                try:
                    return f"{float(val):.2f}"
                except (TypeError, ValueError):
                    return "N/A"

            temp = format_val(latest_feed.get("field1"))
            humidity = format_val(latest_feed.get("field2"))
            dust = format_val(latest_feed.get("field3"))
            aqi = latest_feed.get("field4", "N/A")  # Keep AQI as is (usually integer)

            # Compact SMS format due to character limits
            return f"Home Status:\nT: {temp}C\nH: {humidity}%\nD: {dust}\nAQI: {aqi}"

    async def _handle_whois(self, query: str) -> str:
        """Example handler for contact/user lookup commands."""
        parts = query.split(maxsplit=1)
        target = parts[1] if len(parts) > 1 else "unknown"
        
        # Insert your database or external lookup logic here
        return f"Contact Info for {target}:\nPhone: +1-555-0199\nEmail: {target}@example.com"