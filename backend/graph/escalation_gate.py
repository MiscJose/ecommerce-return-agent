from .state import ReturnState
from langgraph.types import interrupt

def escalation_gate(state: ReturnState) -> ReturnState:
    total_amount = state['total_amount']

    if total_amount >= 150:
        response = interrupt(f"Do you approve or deny this return of ${total_amount}")
        status = None
        if response == "approved":
            status = "accepted"
        else:
            status = "denied"
        return {"status": status}
   
    else:
        return {"status": "accepted"}
   