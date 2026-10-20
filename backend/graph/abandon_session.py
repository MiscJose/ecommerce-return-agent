from .state import ReturnState
from langchain.messages import AIMessage

def abandon_session(state: ReturnState) -> ReturnState:
   ai_msg = AIMessage("You have reached the end of retry attempts. Session is closing", additional_kwargs={"channel": "customer"})
   return {"messages": [ai_msg]}