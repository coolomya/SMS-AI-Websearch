# graph/edges.py
import logging
from graph.state import GraphState
from config.settings import settings
from services.llm.router import LLMRouter

logger = logging.getLogger("search_assistant")
llm_router = LLMRouter()

async def route_after_search(state: GraphState) -> str:
    """Evaluates search results content structure using the LLM Router Judge."""
    logger.info("--- [Edge Evaluation] Analyzing search context quality ---")
    
    # FIX: Unpack the tuple to get the boolean verdict separately from token usage maps
    is_valid, _ = await llm_router.evaluate_quality(
        query=state["query"], 
        content=state["context"]
    )
    
    if is_valid:
        logger.info("✅ [Judge Verdict] Context APPROVED. Proceeding to summary generation.")
        return "generate_sms"
        
    if state["search_retry_count"] >= settings.MAX_RETRY_COUNT:
        logger.warning("❌ [Judge Verdict] Context REJECTED & search limits exceeded. Routing to LLM Knowledge Base...")
        return "fallback"
        
    logger.info("❌ [Judge Verdict] Context REJECTED. Retrying search query step...")
    return "retry_search"

async def route_after_sms(state: GraphState) -> str:
    """Evaluates final SMS quality requirements (length limit, structure, syntax)."""
    logger.info("--- [Edge Evaluation] Analyzing generated SMS draft constraints ---")
    
    # FIX: Unpack the tuple here as well
    is_valid, _ = await llm_router.evaluate_quality(
        query=state["query"], 
        content=state["sms_output"]
    )
    
    if is_valid:
        logger.info("✅ [SMS Verdict] Draft APPROVED. Terminating graph state safely.")
        return "end"
        
    if state["llm_retry_count"] >= settings.MAX_RETRY_COUNT:
        logger.warning("❌ [SMS Verdict] Draft REJECTED & retry limits breached. Escalating to Fallback...")
        return "fallback"
        
    logger.info("❌ [SMS Verdict] Draft REJECTED. Triggering re-generation pass...")
    return "retry_sms"
