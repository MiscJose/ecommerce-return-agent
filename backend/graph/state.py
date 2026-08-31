from datetime import date
from decimal import Decimal

from typing import TypedDict, Annotated
from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import END, START, StateGraph


class ReturnState(TypedDict):
   order_id: int
   order_id_attempts: int
   return_reason: str
   order_date: date
   vip_status: bool
   return_items_total: Decimal
   latest_return_date: date
   reason_category: str
   status: str
   escalation_reason: str 
   messages: Annotated[list[AnyMessage], add_messages]

default_return_state = {
   "order_id": None,
   "order_id_attempts": 0,
   "return_reason": None,
   "order_date": None,
   "vip_status": False,
   "return_items_total": Decimal('0.0'),
   "latest_return_date": None,
   "reason_category": None,
   "status": "pending",
   "escalation_reason": None,
   "messages": []
}

def order_finder(state: ReturnState) -> ReturnState:
   print("Function order_finder")
   return {}

def eligibility_gate(state: ReturnState) -> ReturnState:
   print("Function eligibility_gate")
   return {}

def escalation_gate(state: ReturnState) -> ReturnState:
   print("Function escalation_gate")
   return {}

def finalize_return(state: ReturnState) -> ReturnState:
   print("Function finalize_return")
   return {}

def route_eligibility(state: ReturnState) -> str:
   print("Function route_eligibility")
   return "eligible"

builder = StateGraph(ReturnState)

builder.add_node("order_finder", order_finder)
builder.add_node("eligibility_gate", eligibility_gate)
builder.add_node("escalation_gate", escalation_gate)
builder.add_node("finalize_return", finalize_return)

builder.add_edge(START, "order_finder")
builder.add_edge("order_finder", "eligibility_gate")
builder.add_conditional_edges("eligibility_gate", route_eligibility, {"eligible": "escalation_gate", "ineligible": "finalize_return"})
builder.add_edge("escalation_gate", "finalize_return")
builder.add_edge("finalize_return", END)

graph = builder.compile()