from .state import ReturnState
from langgraph.types import interrupt

def route_order_finder(state: ReturnState) -> str:
   order_id, order_id_attempts = state.get("order_id"), state.get("order_id_attempts")
   if order_id is not None:
      return "found"
   elif order_id_attempts >=3:
      return "exhausted"
   else:
      return "retry"