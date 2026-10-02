from .state import ReturnState
from helper import check_window
from langchain.messages import AIMessage, HumanMessage

from langgraph.types import interrupt

def eligibility_gate(state: ReturnState) -> ReturnState:
    order_date = state["order_date"]
    vip_status = state["vip_status"]

    within_window = check_window(order_date, vip_status)

    if within_window:
        additional_kwargs = {"channel": "customer"}
        ai_msg = "What is your return reason?"
        human_msg = interrupt({"question": ai_msg, "additional_kwargs": additional_kwargs})
        messages = [AIMessage(ai_msg, additional_kwargs=additional_kwargs), HumanMessage(human_msg, additional_kwargs=additional_kwargs)]
        return {"return_reason": human_msg} | {"messages": messages}
        
    else:
        return {"status": "denied", "auto_deny_reason": "return window expired"}
   
    