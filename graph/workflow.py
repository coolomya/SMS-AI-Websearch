# graph/workflow.py
from langgraph.graph import StateGraph, START, END
from graph.state import GraphState
from graph.nodes import query_searXNG_node, llm_summary_sms_node, llm_knowledge_base_node, static_default_sms_node
from graph.edges import route_after_search, route_after_sms

builder = StateGraph(GraphState)

# 1. Register all structural processing nodes
builder.add_node("search_node", query_searXNG_node)
builder.add_node("sms_node", llm_summary_sms_node)
builder.add_node("kb_fallback_node", llm_knowledge_base_node)
builder.add_node("static_fallback_node", static_default_sms_node) # The ultimate safety line

# 2. Map structural execution edges
builder.add_edge(START, "search_node")

builder.add_conditional_edges(
    "search_node",
    route_after_search,
    {
        "generate_sms": "sms_node",
        "retry_search": "search_node",
        "fallback": "kb_fallback_node" # Route first to LLM knowledge base query
    }
)

builder.add_conditional_edges(
    "sms_node",
    route_after_sms,
    {
        "end": END,
        "retry_sms": "sms_node",
        "fallback": "kb_fallback_node" # Route first to LLM knowledge base query
    }
)

# 3. Handle downstream conditions from the knowledge base node
builder.add_conditional_edges(
    "kb_fallback_node",
    # If the KB node successfully populated sms_output, exit graph. Else, go to static fallback.
    lambda state: "end" if state.get("sms_output") else "static_critical",
    {
        "end": END,
        "static_critical": "static_fallback_node"
    }
)

# 4. Terminal edge from static node to complete state loop
builder.add_edge("static_fallback_node", END)

compiled_graph = builder.compile()
