from .state import ReturnState
from langchain.messages import AIMessage
import os
import psycopg2

def finalize_return(state: ReturnState) -> ReturnState:
   order_id, total_amount, status, return_reason, reason_category, auto_deny_reason = state["order_id"], state['total_amount'], state['status'], state.get('return_reason'), state.get('reason_category'), state.get('auto_deny_reason')

   conn, cur = None, None 
   try:
      conn = psycopg2.connect(os.getenv("DATABASE_URL"))
      cur = conn.cursor()

      query = "insert into returns (order_id, return_amount, return_status, return_reason, return_reason_category) VALUES (%s, %s, %s, %s, %s); "

      cur.execute(query, (order_id, total_amount, status, return_reason, reason_category))
      conn.commit()

      closing_message = ''
      if status == "accepted":
         closing_message = f"Congratulations! Your order of ${total_amount} has been approved. Please wait 3-5 business day for your return to be processed."
      else:
         if auto_deny_reason == 'return window expired':
            closing_message = "Unfortunately your return window has expired and a return can no longer be processed. Have a good day."
         else:
            closing_message = "Unfortunately your return was not approved by a manager. Have a good day."

      ai_msg = AIMessage(closing_message, additional_kwargs={"channel": "customer"})

      return {"messages": [ai_msg]}

   except psycopg2.Error as e:
      print(f"DB Error: {e}")
      return None 

   finally:
      if cur:
         cur.close()
      if conn:
         conn.close()

   
