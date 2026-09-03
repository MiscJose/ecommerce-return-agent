from .state import ReturnState
from langgraph.types import interrupt, Command

def route_eligibility(state: ReturnState) -> str:
   print("Function route_eligibility")

   return "eligible"