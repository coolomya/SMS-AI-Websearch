# graph/nodes.py
import logging
from graph.state import GraphState
from services.search.searxng import SearXNGClient
from services.llm.router import LLMRouter

logger = logging.getLogger("search_assistant")
search_client = SearXNGClient()
llm_router = LLMRouter()

async def query_searXNG_node(state: GraphState) -> dict:
    current_retry = state['search_retry_count']
    logger.info(f"--- [Node] Processing Query: '{state['query']}' (Search Attempt {current_retry + 1}) ---")
    
    combined_context = await search_client.fetch_results(
        query=state['query'], 
        retry_count=current_retry
    )
    
    logger.info(
        f"\n--- 🔍 INTERMEDIATE DATA: SearXNG Content (Attempt {current_retry + 1}) ---\n"
        f"{combined_context[:500]}...\n"
        f"----------------------------------------------------------------------"
    )
    return {
        "context": combined_context, 
        "search_retry_count": current_retry + 1
    }

async def llm_summary_sms_node(state: GraphState) -> dict:
    current_retry = state['llm_retry_count']
    logger.info(f"--- [Node] Invoking Router Pipelines (SMS Attempt {current_retry + 1}) ---")
    
    # Destructure both response string and token metadata maps cleanly
    raw_draft, tokens = await llm_router.generate_sms(state['query'], state['context'])
    
    # Safely extract and fallback accumulate totals
    new_prompt_total = state.get('total_prompt_tokens', 0) + tokens.get('prompt_tokens', 0)
    new_completion_total = state.get('total_completion_tokens', 0) + tokens.get('completion_tokens', 0)
    
    logger.info(
        f"\n--- 🤖 ACCUMULATED METRICS ---\n"
        f"Cumulative Prompt Tokens: {new_prompt_total}\n"
        f"Cumulative Completion Tokens: {new_completion_total}\n"
        f"------------------------------"
    )
    
    return {
        "sms_output": raw_draft, 
        "llm_retry_count": current_retry + 1,
        "total_prompt_tokens": new_prompt_total,
        "total_completion_tokens": new_completion_total
    }

