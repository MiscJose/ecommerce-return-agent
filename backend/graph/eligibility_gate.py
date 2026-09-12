from .state import ReturnState
from helper import check_window

from langgraph.types import interrupt

def eligibility_gate(state: ReturnState) -> ReturnState:
    order_date = state["order_date"]
    vip_status = state["vip_status"]

    within_window = check_window(order_date, vip_status)

    if within_window:
        return_reason = interrupt("What is your return reason?")
        return {"return_reason": return_reason}
        
    else:
        return {"status": "denied", "auto_deny_reason": "return window expired"}
   
    