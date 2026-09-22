# Standard library
import os
from contextlib import asynccontextmanager
from uuid import uuid4

# Third-party
from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg2
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

# Local
from graph.state import default_return_state
from graph.build_graph import builder

load_dotenv()


class ResumeRequest(BaseModel):
    thread_id: str
    customer_answer: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_uri = os.getenv("DATABASE_URL")
    async with AsyncPostgresSaver.from_conn_string(db_uri) as checkpointer:
        await checkpointer.setup()
        app.state.graph = builder.compile(checkpointer=checkpointer)
        yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def health_check():
    return {"status": "ok"}

@app.get("/orders")
async def get_order(order_id):
    conn, cur = None, None 
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
async def start_conversation(req: Request):
    try:
        thread_id = str(uuid4())
        # thread_id = 'state-0'
        config = {"configurable": {"thread_id": thread_id}}
        result = await req.app.state.graph.ainvoke(default_return_state.copy(), config)
        return {"thread_id": thread_id, "question": result['__interrupt__'][0].value}
    except Exception as e:
        return {"Error": str(e)}

@app.post("/returns/resume")
async def resume_conversation(request: ResumeRequest, req: Request):
    try:
        resume_command = Command(resume=request.customer_answer)
        config = {"configurable": {"thread_id": request.thread_id}}
        result = await req.app.state.graph.ainvoke(resume_command, config)
        return {"thread_id": request.thread_id, "result": result}
    except Exception as e:
        return {"Error": str(e)}

@app.post("/admin/reset-demo")
async def reset_demo(x_reset_secret: str = Header(None)):
    if x_reset_secret != os.getenv("RESET_SECRET"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        conn, cur = None, None
        try:
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            cur = conn.cursor()

            truncate_query = "TRUNCATE returns RESTART IDENTITY CASCADE;"
            with open("./reset/re_seed.sql", 'r', encoding='utf-8') as f:
                re_seed_query =  f.read()

            cur.execute(truncate_query)
            cur.execute(re_seed_query)
            conn.commit()

            return {"Status": "Reset Complete"}
        
        except psycopg2.Error as e:
            return {"Error": str(e)}
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

