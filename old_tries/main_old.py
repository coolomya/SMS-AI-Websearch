import requests

SEARXNG_URL = "http://localhost:8080/search"

# 1. Add Browser Headers so SearXNG locks into English
HEADERS = {
    "User-Agent": "Mozilla/5.5 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9"  # Tell engines you only want English
}

# 2. Use 'language' parameter inside the query dictionary
PARAMS = {
    "q": "what is the capital of india",
    "format": "json",
    "engines": "google,bing",
    "language": "en-US"  # Forces SearXNG to target English locales
}

try:
    # Pass BOTH headers and params
    response = requests.get(SEARXNG_URL, params=PARAMS, headers=HEADERS)
    response.raise_for_status()
    
    data = response.json()
    results = data.get("results", [])
    
    print(f"--- Found {len(results)} results ---\n")
    for index, result in enumerate(results[:5], 1):
        print(f"{index}. {result.get('title')}")
        print(f"   URL: {result.get('url')}")
        print(f"   Language Tracked: {result.get('language', 'Unknown')}\n")

except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
