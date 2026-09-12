import logging
import os
from flask import Flask, request, jsonify
import requests
import ollama

app = Flask(__name__)

# 1. Configure the Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("search_assistant.log", encoding="utf-8"), # Saves logs to this file
        logging.StreamHandler()                                       # Keeps logging to the console terminal
    ]
)

SEARXNG_URL = "http://localhost:8080/search"
HEADERS = {
    "User-Agent": "Mozilla/5.5 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

@app.route('/search', methods=['GET'])
def handle_search():
    # Capture client connection details
    client_ip = request.remote_addr
    user_query = request.args.get('q', '').strip()
    
    logging.info(f"Incoming request from IP: {client_ip} | Query: '{user_query}'")
    
    if not user_query:
        logging.warning(f"Rejected empty query request from IP: {client_ip}")
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    # 2. Fetch data from local SearXNG instance
    PARAMS = {
        "q": user_query,
        "format": "json",
        "engines": "google,bing,wikipedia",
        "language": "en-US"
    }

    try:
        logging.info(f"Forwarding query '{user_query}' to SearXNG...")
        response = requests.get(SEARXNG_URL, params=PARAMS, headers=HEADERS)
        response.raise_for_status()
        search_data = response.json()
        results = search_data.get("results", [])
        
        if not results:
            logging.info(f"SearXNG returned 0 results for query: '{user_query}'")
            return jsonify({"sms_summary": "No search results returned from SearXNG."})
            
        snippets = []
        for index, res in enumerate(results[:5], 1):
            snippets.append(f"Result {index}: {res.get('title', '')} - {res.get('content', '')}")
        context = "\n".join(snippets)
        logging.info(f"Successfully gathered {len(results[:5])} results from SearXNG.")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"SearXNG connection failed for query '{user_query}': {str(e)}")
        return jsonify({"error": f"SearXNG connection error: {str(e)}"}), 500

    # 3. Process via Ollama
    system_prompt = (
        "You are an assistant preparing a short, highly accurate answer for an SMS dispatch.\n"
        "Your task is to answer the user's specific question using ONLY the relevant search results provided.\n"
        "CRITICAL RULES:\n"
        "1. Identify the user's core question. Throw away any search snippets that are unrelated ads, corporate boilerplate, or website navigation links.\n"
        "2. Do not mix unrelated topics together. Focus exclusively on the answer to the user's intent.\n"
        "3. Keep the output strictly under 150 words.\n"
        "4. Do not include markdown bolding, asterisks (*), headers, lists, introductory phrases, or filler text. Write it as one continuous, easily readable text message."
    )
    
    try:
        logging.info(f"Sending context to Ollama (llama3.2:3b) for query: '{user_query}'...")
        sms_response = ollama.generate(
            model='llama3.2:3b',
            system=system_prompt,
            prompt=f"User Question: {user_query}\n\nSearch Context:\n{context}\n\nSMS Summary:"
        )
        final_sms = sms_response['response'].strip()
        word_count = len(final_sms.split())
        
        logging.info(f"Successfully generated summary. Word Count: {word_count}")
        
        return jsonify({
            "query": user_query,
            "sms_summary": final_sms,
            "word_count": word_count
        })
        
    except Exception as e:
        logging.error(f"Ollama execution failed for query '{user_query}': {str(e)}")
        return jsonify({"error": f"Ollama execution error: {str(e)}"}), 500

if __name__ == '__main__':
    logging.info("Starting local Wi-Fi Search Assistant Server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False) # Turned debug off to keep logs clean
