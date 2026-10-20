from .state import ReturnState
from langchain.chat_models import init_chat_model
import os

from typing import Literal, get_args
from pydantic import BaseModel

response_category = Literal["Changed Mind", "Defective", "Incorrect Items Delivered", "Other"]

class ResponseSchema(BaseModel):
    response_category: response_category

def classify_reason(state: ReturnState) -> ReturnState:
    return_reason = state['return_reason']

    try:
        model = init_chat_model(
            model=os.getenv('LLM_MODEL')
        )
        structured_model = model.with_structured_output(ResponseSchema)
        result = structured_model.invoke(f'You are a retial returns agent and will categorize the following human return reason: {return_reason} into one of four categories: {get_args(response_category)}')
        return_category = result.response_category
    except Exception as e:
        print(f"This failed with error: {e}")
        return_category = "Other"
    return {"reason_category": return_category}
    