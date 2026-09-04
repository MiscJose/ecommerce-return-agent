from .state import ReturnState
from langgraph.types import interrupt, Command

def route_eligibility_gate(state: ReturnState) -> str:
   print("Function route_eligibility_gate")

   return "eligible"