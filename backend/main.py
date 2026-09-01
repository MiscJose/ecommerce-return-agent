import os

from fastapi import FastAPI
import psycopg2

from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel

class Order(BaseModel):
    order_id: str

app = FastAPI()


@app.get("/customers")
async def get_customers():
    conn, cur = None, None
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        cur.execute("select * from users")
        users = cur.fetchall()

        return {"users": users}
    
    except psycopg2.Error as e:
        return {"Error": str(e)}

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

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

@app.post("/orders")
async def send_order(order: Order):
    return Order



