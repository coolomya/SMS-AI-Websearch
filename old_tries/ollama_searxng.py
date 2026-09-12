import requests
import ollama

# Configuration constants
SEARXNG_URL = "http://localhost:8080/search"
HEADERS = {
    "User-Agent": "Mozilla/5.5 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

print("====================================================")
print("  SearXNG + Ollama SMS Generator CLI Loop Active    ")
print("  Type 'exit' or 'quit' to terminate the program.    ")
print("====================================================\n")

while True:
    user_query = input("\nEnter your search query: ").strip()
    
    if user_query.lower() in ['exit', 'quit']:
        print("Exiting application. Goodbye!")
        break
        
    if not user_query:
        print("Query cannot be empty. Please try again.")
        continue

    print(f"Searching SearXNG for: '{user_query}'...")
    
    PARAMS = {
        "q": user_query,
        "format": "json",
        "engines": "google,bing,wikipedia",  # Added wikipedia to improve definition accuracy
        "language": "en-US"
    }

    try:
        response = requests.get(SEARXNG_URL, params=PARAMS, headers=HEADERS)
        response.raise_for_status()
        search_data = response.json()
        results = search_data.get("results", [])
        
        if not results:
            print("No search results returned from SearXNG. Skipping LLM step.")
            continue
            
        snippets = []
        for index, res in enumerate(results[:5], 1):  # Take top 5 results
            title = res.get('title', '')
            content = res.get('content', '')
            snippets.append(f"Result {index}: {title} - {content}")
        
        context = "\n".join(snippets)
        
    except requests.exceptions.RequestException as e:
        print(f"Error pulling from SearXNG: {e}")
        continue

    print("Generating SMS summary via llama3.2:3b...")
    
    # UPDATED: Added strict filtering rules for the AI model
    system_prompt = (
        "You are an assistant preparing a short, highly accurate answer for an SMS dispatch.\n"
        "Your task is to answer the user's specific question using ONLY the relevant search results provided.\n"
        "CRITICAL RULES:\n"
        "1. Identify the user's core question. Throw away any search snippets that are unrelated ads, corporate boilerplate, or website navigation links (e.g. Microsoft logins, generic cookie notices, or irrelevant search noise).\n"
        "2. Do not mix unrelated topics together. Focus exclusively on the answer to the user's intent.\n"
        "3. Keep the output strictly under 150 words.\n"
        "4. Do not include markdown bolding, asterisks (*), headers, lists, introductory phrases, or filler text. Write it as one continuous, easily readable text message."
    )
    
    user_prompt = f"User Question: {user_query}\n\nSearch Context:\n{context}\n\nSMS Summary:"
    
    try:
        sms_response = ollama.generate(
            model='llama3.2:3b',
            system=system_prompt,
            prompt=user_prompt
        )
        
        final_sms = sms_response['response'].strip()
        
        print("\n--- Your SMS Summary (under 150 words) ---")
        print(final_sms)
        print(f"------------------------------------------")
        print(f"Word count: {len(final_sms.split())}")
        
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
