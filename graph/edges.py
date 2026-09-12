import logging
from graph.state import GraphState
from config.settings import settings
from services.llm.router import LLMRouter

logger = logging.getLogger("search_assistant")
llm_router = LLMRouter()

async def route_after_search(state: GraphState) -> str:
    """Evaluates search results content structure using the LLM Router Judge."""
    logger.info("--- [Edge Evaluation] Analyzing search context quality ---")
    
    is_valid = await llm_router.evaluate_quality(
        query=state["query"], 
        content=state["context"]
    )
    
    if is_valid:
        logger.info("   [Edge Decision] Context verified. Proceeding to summary generation.")
        return "generate_sms"
        
    if state["search_retry_count"] >= settings.MAX_RETRY_COUNT:
        logger.warning("   [Edge Decision] Search limits exceeded. Route directly to fallback output.")
        return "fallback"
        
    logger.info("   [Edge Decision] Context rejected. Retrying with updated engine map.")
    return "retry_search"

async def route_after_sms(state: GraphState) -> str:
    """Evaluates final SMS quality requirements (length limit, structure, syntax)."""
    logger.info("--- [Edge Evaluation] Analyzing generated SMS draft constraints ---")
    
    is_valid = await llm_router.evaluate_quality(
        query=state["query"], 
        content=state["sms_output"]
    )
    
    if is_valid:
        logger.info("   [Edge Decision] Output meets structural metrics. Terminating graph.")
        return "end"
        
    if state["llm_retry_count"] >= settings.MAX_RETRY_COUNT:
        logger.warning("   [Edge Decision] LLM generation thresholds breached. Route to fallback execution.")
        return "fallback"
        
    logger.info("   [Edge Decision] Draft failed requirements metrics. Executing re-generation pass.")
    return "retry_sms"
