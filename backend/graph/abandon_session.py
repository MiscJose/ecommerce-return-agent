from .state import ReturnState, AIMessage

def abandon_session(state: ReturnState) -> ReturnState:
   ai_msg = AIMessage("You have reached the end of retry attempts. Session is closing")
   return {"messages": [ai_msg]}