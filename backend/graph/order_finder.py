from .state import ReturnState
from langgraph.types import interrupt

from helper import find_order

def order_finder(state: ReturnState) -> ReturnState:

   order_id_attempts = state.get('order_id_attempts')
   if order_id_attempts == 3:
      return {}
   
   customer_response = interrupt("What is your order id?")
   customer_response = customer_response.strip()
   order = find_order(customer_response)

   if not order:
      order_id_attempts+=1
      return {"order_id_attempts": order_id_attempts}

   return order