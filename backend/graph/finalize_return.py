from .state import ReturnState
from langchain.messages import AIMessage
import os
import psycopg2

def finalize_return(state: ReturnState) -> ReturnState:
   order_id, total_amount, status, return_reason = state["order_id"], state['total_amount'], state['status'], state.get('return_reason')

   conn, cur = None, None 
   try:
      conn = psycopg2.connect(os.getenv("DATABASE_URL"))
      cur = conn.cursor()

      query = "insert into returns (order_id, return_amount, return_status, return_reason) VALUES (%s, %s, %s, %s); "

      cur.execute(query, (order_id, total_amount, status, return_reason))

      ai_msg = AIMessage("Have a good day!")
      return {"messages": [ai_msg]}

   except psycopg2.Error as e:
      print(f"DB Error: {e}")
      return None 

   
