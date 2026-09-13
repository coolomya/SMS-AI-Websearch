from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from graph.workflow import compiled_graph
from config.settings import settings 
from services.llm.router import LLMRouter
from pydantic import BaseModel
import logging

logger = logging.getLogger("search_assistant")

router = APIRouter()

def sanitize_query(text: str) -> str:
    """Removes blacklisted words and condenses multiple lines into a single line."""
    # Use the active configuration parameters
    for word in settings.BANNED_WORDS:
        text = text.replace(word, "")
    
    single_line_text = " ".join([line.strip() for line in text.splitlines() if line.strip()])
    return single_line_text

@router.get("/search-assistant", summary="Query State Graph Workflow Pipeline")
async def execute_search_assistant_pipeline(q: str = Query(..., description="The query to process")):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query payload parameter cannot be left empty.")

    # Apply the cleanup logic to remove banned words and force a single line
    q = sanitize_query(q)
    
    # Final check just in case the sanitization left the query completely empty
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query is empty after text sanitization.")
    
    try:
        # Construct pipeline root runtime execution dictionary structure
        initial_state = {
            "query": q,
            "context": "",
            "sms_output": "",
            "search_retry_count": 0,
            "llm_retry_count": 0,
            "total_prompt_tokens": 0, 
            "total_completion_tokens": 0
        }
        
        # Stream or invoke asynchronous execution through the engine graph layout
        final_state = await compiled_graph.ainvoke(initial_state)
        content={
                        "status": "success",
                        "query": final_state["query"],
                        "sms_response": final_state["sms_output"],
                        "metrics": {
                            "search_retries": final_state["search_retry_count"],
                            "llm_retries": final_state["llm_retry_count"],
                            "total_prompt_tokens": final_state["total_prompt_tokens"],
                            "total_completion_tokens": final_state["total_completion_tokens"]
                        }
                    }
        logger.info(f"Responding : {content}")
        return JSONResponse(
            content
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph internal processing execution fault: {str(e)}")

# Initialize your decoupled router service instance
llm_router = LLMRouter()

class LLMTestPayload(BaseModel):
    query: str
    context: str

@router.post("/test-llm", summary="Direct LLM Router Sandbox Endpoint (Bypasses Search)")
async def test_llm_routing_layer(payload: LLMTestPayload):
    """
    Directly tests the LLM orchestration layer.
    Allows validation of the primary (OpenAI) -> fallback (Ollama) routing behavior.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query payload parameter cannot be left empty.")
        
    try:
        # 1. Execute direct SMS summary text generation pass
        generated_sms = await llm_router.generate_sms(
            query=payload.query, 
            context=payload.context
        )
        
        # 2. Execute explicit quality validation edge criteria pass
        quality_assessment = await llm_router.evaluate_quality(
            query=payload.query, 
            content=generated_sms
        )
        
        return JSONResponse(
            content={
                "status": "success",
                "component_tested": "LLMRouter Layer",
                "input_query": payload.query,
                "input_context": payload.context,
                "generated_sms": generated_sms,
                "passed_llm_judge": quality_assessment
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Direct LLM Router processing execution fault: {str(e)}"
        )
