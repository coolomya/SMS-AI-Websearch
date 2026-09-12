import logging
import httpx
import ollama
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# --- 1. Logging Configuration (Dual Stream: CLI + File, Fixes Duplication) ---
logger = logging.getLogger("search_assistant")
logger.setLevel(logging.INFO)
logger.propagate = False  # Stops logs from bubbling up to root and doubling inside Uvicorn

if not logger.handlers:
    log_format = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # Stream 1: Output directly to your CLI Terminal Window
    cli_handler = logging.StreamHandler()
    cli_handler.setFormatter(log_format)
    logger.addHandler(cli_handler)

    # Stream 2: Output to your physical log file for auditing
    file_handler = logging.FileHandler("search_assistant.log", encoding="utf-8")
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

# --- 2. Initialize FastAPI ---
app = FastAPI(title="Async LangGraph Search Assistant")

# --- 3. Define the Graph State ---
class GraphState(TypedDict):
    query: str
    context: str
    sms_output: str
    search_retry_count: int
    llm_retry_count: int

MAX_RETRY_COUNT = 3
SEARXNG_URL = "http://localhost:8080/search"

# --- 4. Async Helper LLM Judge (Fixed Prompt System for 3b Models) ---
async def async_llm_judge(query: str, content_to_evaluate: str) -> bool:
    """Asynchronously evaluates data quality and length correctness via Ollama."""
    if not content_to_evaluate.strip():
        return False
        
    # Check if we are judging an intermediate context or a final SMS draft
    # SMS drafts are typically under 150 characters and don't look like raw data lists
    is_sms_draft = len(content_to_evaluate) <= 200 
    
    system_instruction = (
        "You are a strict quality control judge system. Your job is to output exactly "
        "one word and nothing else. You are forbidden from writing explanations, notes, "
        "or markdown packaging."
    )
    
    if is_sms_draft:
        # Custom evaluation criteria tailored for short SMS payloads
        judge_prompt = (
            f"Analyze the following SMS response draft against the User Query.\n\n"
            f"User Query: {query}\n"
            f"SMS Draft: {content_to_evaluate}\n\n"
            f"CRITERIA:\n"
            f"1. Is the text written completely in English?\n"
            f"2. Does it provide a meaningful, positive response or direct answer to the query?\n"
            f"3. Is it brief, concise, and under 150 characters?\n\n"
            f"If ALL criteria are met, output: TRUE\n"
            f"If it fails any criterion, output: FALSE"
        )
    else:
        # Standard criteria for judging raw SearXNG search result pages
        judge_prompt = (
            f"Analyze the following search context against the User Query.\n\n"
            f"User Query: {query}\n"
            f"Search Context: {content_to_evaluate}\n\n"
            f"CRITERIA:\n"
            f"1. Does the content contain text that could help answer the query?\n"
            f"2. Is the content written primarily in English?\n\n"
            f"If BOTH criteria are met, output: TRUE\n"
            f"If either criterion fails, output: FALSE"
        )
    
    try:
        response = ollama.generate(
            model='llama3.2:3b', 
            system=system_instruction, 
            prompt=judge_prompt
        )
        verdict = response['response'].strip().upper()
        logger.info(f"   [Judge Process] Raw response received: '{verdict}'")
        return "TRUE" in verdict
    except Exception as e:
        logger.error(f"Judge verification failed: {e}")
        return False

# --- 5. Define Asynchronous Nodes ---
async def query_searXNG_node(state: GraphState) -> dict:
    current_retry = state['search_retry_count']
    logger.info(f"--- [Node] Querying SearXNG (Attempt {current_retry + 1}) ---")
    
    headers = {"User-Agent": "Mozilla/5.5 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept-Language": "en-US,en;q=0.9"}
    search_query = state['query']
    
    # Default engine mix
    engine_selection = "google,bing,duckduckgo,brave,wikipedia"
    
    # STRATEGY CHANGE: If Attempt 1 returned junk, drop Google/Bing completely for retries 
    # and isolate the search to high-reliability encyclopedic engines.
    if current_retry > 0:
        engine_selection = "wikipedia,duckduckgo,brave"
        logger.info(f"   [Search Strategy] Switched engine routing target to: {engine_selection}")

    params = {
        "q": search_query, 
        "format": "json", 
        "engines": engine_selection, 
        "language": "en-US"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(SEARXNG_URL, params=params, headers=headers, timeout=6.0)
            res.raise_for_status()
            results = res.json().get("results", [])
            
            snippets = [f"{r.get('title')} - {r.get('content')}" for r in results[:5]]
            combined_context = "\n".join(snippets)
            
            logger.info(
                f"\n--- 🔍 INTERMEDIATE DATA: SearXNG Raw Output (Attempt {current_retry + 1}) ---\n"
                f"{combined_context if combined_context else '[Empty Context Passed]'}\n"
                f"----------------------------------------------------------------------"
            )
            
            return {
                "context": combined_context, 
                "search_retry_count": current_retry + 1
            }
        except Exception as e:
            logger.error(f"SearXNG Fetch Failed: {e}")
            return {"context": "", "search_retry_count": current_retry + 1}

async def llm_summary_sms_node(state: GraphState) -> dict:
    current_retry = state['llm_retry_count']
    logger.info(f"--- [Node] Generating LLM SMS (Attempt {current_retry + 1}) ---")
    
    system_prompt = (
        "Summarize the provided search results to directly answer the user query. "
        "CRITICAL: The entire response must be strictly under 150 characters total. "
        "Write only one short, direct sentence. No markdown, no bolding, no extra text."
    )

    user_prompt = f"User Question: {state['query']}\n\nSearch Context:\n{state['context']}\n\nSMS Summary:"
    
    try:
        response = ollama.generate(model='llama3.2:3b', system=system_prompt, prompt=user_prompt)
        # Extract and slice strictly to 150 characters
        raw_draft = response['response'].strip()[:150]
        
        logger.info(
            f"\n--- 🤖 INTERMEDIATE DATA: LLM SMS Draft (Attempt {current_retry + 1}) ---\n"
            f"{raw_draft}\n"
            f"--------------------------------------------------------------------"
        )
        
        return {
            "sms_output": raw_draft, 
            "llm_retry_count": current_retry + 1
        }

    except Exception as e:
        logger.error(f"Ollama generation failed: {e}")
        return {"sms_output": "", "llm_retry_count": current_retry + 1}
async def static_default_sms_node(state: GraphState) -> dict:
    # Instead of a generic error, we fetch the draft that was generated on Attempt 3
    last_draft = state.get("sms_output", "").strip()
    
    if last_draft:
        logger.warning(
            f"--- [Node] Max Retries Exhausted. Falling back to the last generated draft for auditing ---"
        )
        return {"sms_output": last_draft}
    else:
        # Emergency backup if the text string was completely empty
        fallback = f"Sorry, I couldn't safely process your request for '{state['query']}' right now."
        return {"sms_output": fallback}

# --- 6. Async Conditional Routing Edges ---
async def route_after_search(state: GraphState) -> str:
    is_ans_correct = await async_llm_judge(state['query'], state['context'])
    
    if is_ans_correct:
        logger.info("   -> Judge Verdict: Context is GOOD. Moving to LLM node.")
        return "llm_summary_sms"
    
    if state['search_retry_count'] >= MAX_RETRY_COUNT:
        logger.warning("   -> Judge Verdict: Context BAD but Max Search Retries hit. Forcing to LLM node.")
        return "llm_summary_sms"
        
    logger.info("   -> Judge Verdict: Context BAD. Retrying Search Engine loop.")
    return "query_searXNG"


async def route_after_llm(state: GraphState) -> str:
    is_ans_correct = await async_llm_judge(state['query'], state['sms_output'])
    
    if is_ans_correct:
        logger.info("   -> Judge Verdict: SMS Output looks EXCELLENT. Terminating workflow.")
        return END
        
    if state['llm_retry_count'] >= MAX_RETRY_COUNT:
        # CRITICAL LOGGING STEP: Explicitly alert that the judge failed but we are saving the text
        logger.warning(
            f"   -> [CRITICAL] Judge rejected draft 3 times. Forcing pass to final output. "
            f"Failing Draft text saved: '{state['sms_output']}'"
        )
        return "static_default_sms"
        
    logger.info("   -> Judge Verdict: SMS Output BAD. Regenerating response.")
    return "llm_summary_sms"

# --- 7. Building the StateGraph Architecture ---
workflow = StateGraph(GraphState)

workflow.add_node("query_searXNG", query_searXNG_node)
workflow.add_node("llm_summary_sms", llm_summary_sms_node)
workflow.add_node("static_default_sms", static_default_sms_node)

workflow.add_edge(START, "query_searXNG")

workflow.add_conditional_edges(
    "query_searXNG",
    route_after_search,
    {"llm_summary_sms": "llm_summary_sms", "query_searXNG": "query_searXNG"}
)
workflow.add_conditional_edges(
    "llm_summary_sms",
    route_after_llm,
    {END: END, "static_default_sms": "static_default_sms", "llm_summary_sms": "llm_summary_sms"}
)
workflow.add_edge("static_default_sms", END)

# Compile the graph
graph_app = workflow.compile()

# --- 8. FastAPI Endpoint Layer ---
@app.get("/search")
async def handle_search_endpoint(q: str = Query(..., description="The query to search and summarize")):
    query_clean = q.strip()
    if not query_clean:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
        
    initial_state = {
        "query": query_clean,
        "context": "",
        "sms_output": "",
        "search_retry_count": 0,
        "llm_retry_count": 0
    }
    
    try:
        logger.info(f"New connection initialized. Processing Request: '{query_clean}'")
        
        # Execute the Graph asynchronously
        final_result = await graph_app.ainvoke(initial_state)
        final_sms = final_result.get("sms_output", "").strip()
        
        # --- AUDIT REPORT ENTRY ---
        logger.info(
            f"\n"
            f"=== 📋 AUDIT REPORT ENTRY ===\n"
            f"USER QUERY : {query_clean}\n"
            f"FINAL ANSWER: {final_sms}\n"
            f"WORD COUNT  : {len(final_sms.split())}\n"
            f"============================="
        )
        
        # <-- 2. Replace your old dict return statement with this:
        return JSONResponse(
            status_code=200,
            content={
                "query": query_clean,
                "sms_summary": final_sms
            },
            headers={
                "Connection": "keep-alive",
                "Content-Type": "application/json"
            }
        )
        
    except Exception as e:
        logger.critical(f"Fatal system fault while resolving graph execution for '{query_clean}': {e}")
        raise HTTPException(status_code=500, detail=f"Graph runtime error: {str(e)}")

        
    except Exception as e:
        logger.critical(f"Fatal system fault while resolving graph execution for '{query_clean}': {e}")
        raise HTTPException(status_code=500, detail=f"Graph runtime error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
