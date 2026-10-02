from .state import ReturnState
from langgraph.types import interrupt
from langchain.messages import HumanMessage, AIMessage

from helper import find_order

def order_finder(state: ReturnState) -> ReturnState:

   order_id_attempts = state.get('order_id_attempts')
   if order_id_attempts == 3:
      return {}

   additional_kwargs = {"channel": "customer"}
   ai_msg = "What is your order id?"
   human_msg = interrupt({"question": ai_msg, "additional_kwargs": additional_kwargs})
   human_msg_clean = human_msg.strip()
   order = find_order(human_msg_clean)

   messages = [AIMessage(ai_msg, additional_kwargs=additional_kwargs), HumanMessage(human_msg, additional_kwargs=additional_kwargs)]

   if not order:
      order_id_attempts+=1
      return {"order_id_attempts": order_id_attempts} | {"messages": messages}

   return order | {"messages": messages}