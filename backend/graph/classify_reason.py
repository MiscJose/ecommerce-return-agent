from .state import ReturnState
from langchain.chat_models import init_chat_model
import os

from typing import Literal
from pydantic import BaseModel

class ResponseSchema(BaseModel):
    response_category: Literal["Changed Mind", "Defective", "Wrong Item Delivered", "Other"]

def classify_reason(state: ReturnState) -> ReturnState:
    return_reason = state['return_reason']

    try:
        model = init_chat_model(
            model=os.getenv('LLM_MODEL')
        )
        structured_model = model.with_structured_output(ResponseSchema)
        result = structured_model.invoke(f'You are a retial returns agent and will categorize the following human return reason: {return_reason} into one of four categories: "Changed Mind", "Defective", "Wrong Item Delivered", "Other"')
        return_category = result.reason_category
    except Exception as e:
        print(f"THIS FAILED AS AN EXCEPTION! {e}")
        return_category = "Other"
    return {"reason_category": return_category}
    