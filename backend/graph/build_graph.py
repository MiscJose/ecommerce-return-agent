from .state import ReturnState
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from .order_finder import order_finder
from .eligibility_gate import eligibility_gate
from .route_order_finder import route_order_finder
from .route_eligibility_gate import route_eligibility_gate
from .escalation_gate import escalation_gate
from .finalize_return import finalize_return



builder = StateGraph(ReturnState)

builder.add_node("order_finder", order_finder)
builder.add_node("eligibility_gate", eligibility_gate)
builder.add_node("escalation_gate", escalation_gate)
builder.add_node("finalize_return", finalize_return)

builder.add_edge(START, "order_finder")
builder.add_conditional_edges("order_finder", route_order_finder, {"found": "eligibility_gate" , "exhausted": "finalize_return" })
builder.add_conditional_edges("eligibility_gate", route_eligibility_gate, {"eligible": "escalation_gate", "ineligible": "finalize_return"})
builder.add_edge("escalation_gate", "finalize_return")
builder.add_edge("finalize_return", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer)

