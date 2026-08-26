from fastapi import FastAPI
import psycopg2

app = FastAPI()


@app.get("/")
async def root():

    conn = psycopg2.connect("dbname=ecommerce_db user=admin password=password")
    cur = conn.cursor()

    cur.execute("select * from users")
    user = cur.fetchone()

    cur.close()
    conn.close()
    
    return {"user": user}