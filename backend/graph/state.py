from datetime import date
from decimal import Decimal

from typing import TypedDict, Annotated
from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages

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


