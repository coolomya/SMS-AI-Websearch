from langgraph.graph import StateGraph, START, END
from graph.state import GraphState
from graph.nodes import query_searXNG_node, llm_summary_sms_node
from graph.edges import route_after_search, route_after_sms

# Internal static node for quick execution handling on absolute failure
async def static_default_sms_node(state: GraphState) -> dict:
    last_draft = state.get("sms_output", "").strip()
    if last_draft:
        return {"sms_output": last_draft}
    return {"sms_output": f"Sorry, I couldn't safely process your request for '{state['query']}' right now."}

# Initialize and construct state architecture machine
builder = StateGraph(GraphState)

# Append computational functional nodes
builder.add_node("search_node", query_searXNG_node)
builder.add_node("sms_node", llm_summary_sms_node)
builder.add_node("fallback_node", static_default_sms_node)

# Map edge connections
builder.add_edge(START, "search_node")

builder.add_conditional_edges(
    "search_node",
    route_after_search,
    {
        "generate_sms": "sms_node",
        "retry_search": "search_node",
        "fallback": "fallback_node"
    }
)

builder.add_conditional_edges(
    "sms_node",
    route_after_sms,
    {
        "end": END,
        "retry_sms": "sms_node",
        "fallback": "fallback_node"
    }
)

builder.add_edge("fallback_node", END)

# Compile framework architecture into single executable runtime object
compiled_graph = builder.compile()
