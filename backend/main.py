import os

from fastapi import FastAPI
import psycopg2

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()


@app.get("/customers")
async def get_customers():
    conn, cur = None, None
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        cur.execute("select * from users")
        users = cur.fetchall()

        cur.close()
        conn.close()
        
        return {"users": users}
    
    except psycopg2.Error as e:
        return {"Error": str(e)}

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
