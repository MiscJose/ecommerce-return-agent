from .state import ReturnState

def route_eligibility_gate(state: ReturnState) -> str:

   return_reason = state.get('return_reason')

   if return_reason is not None:
      return "eligible"
   else:
      return "ineligible"