# graph/state.py
from typing import TypedDict

class GraphState(TypedDict):
    query: str
    context: str
    sms_output: str
    search_retry_count: int
    llm_retry_count: int
    # New analytics fields
    total_prompt_tokens: int
    total_completion_tokens: int
