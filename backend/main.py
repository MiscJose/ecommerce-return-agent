import os

from fastapi import FastAPI
import psycopg2

from uuid import uuid4


from dotenv import load_dotenv
load_dotenv()

from langgraph.types import Command

from graph.state import default_return_state
from graph.build_graph import graph

from pydantic import BaseModel

class ResumeRequest(BaseModel):
    thread_id: str 
    customer_answer: str

app = FastAPI()

@app.get("/orders")
async def get_order(order_id):
    con, cur = None, None 
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        cur.execute(f"select * from orders where order_id={order_id}")
        order = cur.fetchone()

        return order

    except psycopg2.Error as e:
        return {"Error": str(e)}

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()    

@app.post("/returns/start")
async def start_conversation():
    try:
        thread_id = str(uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        result = await graph.ainvoke(default_return_state.copy(), config)
        return {"thread_id": thread_id, "question": result['__interrupt__'][0].value}
    except Exception as e:
        return {"Error": str(e)}

@app.post("/returns/resume")
async def resume_conversation(request: ResumeRequest):
    try:
        resume_command = Command(resume=request.customer_answer)
        config = {"configurable": {"thread_id": request.thread_id}}
        result = await graph.ainvoke(resume_command, config)
        return {"thread_id": request.thread_id, "result": result}
    except Exception as e:
        return {"Error": str(e)}


