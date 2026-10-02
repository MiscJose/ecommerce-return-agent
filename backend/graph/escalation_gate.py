from .state import ReturnState
from langgraph.types import interrupt
from langchain.messages import AIMessage, HumanMessage

def escalation_gate(state: ReturnState) -> ReturnState:
    total_amount = state['total_amount']

    if total_amount >= 150:
        additional_kwargs = {"channel": "manager"}
        ai_msg = f"Do you approve or deny this return of ${total_amount}"
        manager_response = interrupt({"question": ai_msg, "additional_kwargs": additional_kwargs})
        status = None
        if manager_response == "approved":
            status = "accepted"
        else:
            status = "denied"

        messages = [AIMessage(ai_msg, additional_kwargs=additional_kwargs), HumanMessage(manager_response, additional_kwargs=additional_kwargs)]
        return {"status": status, "messages": messages} 
   
    else:
        return {"status": "accepted"}
   