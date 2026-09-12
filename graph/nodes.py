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
    
    raw_draft, tokens = await llm_router.generate_sms(state['query'], state['context'])
    
    new_prompt_total = state.get('total_prompt_tokens', 0) + tokens.get('prompt_tokens', 0)
    new_completion_total = state.get('total_completion_tokens', 0) + tokens.get('completion_tokens', 0)
    
    logger.info(
        f"\n--- 🤖 INTERMEDIATE DATA: LLM SMS Draft Output (Attempt {current_retry + 1}) ---\n"
        f"Draft Text: {raw_draft}\n"
        f"--------------------------------------------------------------------"
    )
    return {
        "sms_output": raw_draft, 
        "llm_retry_count": current_retry + 1,
        "total_prompt_tokens": new_prompt_total,
        "total_completion_tokens": new_completion_total
    }

async def llm_knowledge_base_node(state: GraphState) -> dict:
    """Attempts parameter answering from LLM weights. Safely defaults if models are offline."""
    logger.warning(f"⚠️ [Fallback Node] Consulting internal LLM Knowledge Base for: '{state['query']}'...")
    
    try:
        raw_draft, tokens = await llm_router.generate_from_knowledge_base(state['query'])
        
        return {
            "sms_output": raw_draft,
            "total_prompt_tokens": state.get('total_prompt_tokens', 0) + tokens.get('prompt_tokens', 0),
            "total_completion_tokens": state.get('total_completion_tokens', 0) + tokens.get('completion_tokens', 0)
        }
    except Exception as error_context:
        # CRITICAL SAFETY: If OpenAI is down AND Ollama is completely offline/crashed,
        # catch the exception, log it, and return empty string to trigger the static fallback node.
        logger.error(f"❌ [Critical Error] LLM Knowledge Base layer completely unavailable: {str(error_context)}")
        return {"sms_output": ""}

async def static_default_sms_node(state: GraphState) -> dict:
    """The Ultimate Safety Line: Zero network dependencies, zero LLM dependencies."""
    logger.critical("🚨 [Static Fallback Node] Executing absolute fallback circuit protection.")
    
    last_draft = state.get("sms_output", "").strip()
    if last_draft:
        return {"sms_output": last_draft}
        
    fallback_text = f"Sorry, I couldn't safely process your request for '{state['query']}' right now."
    return {"sms_output": fallback_text}
