import os
import psycopg2

def find_order(order_id):
    conn, cur = None, None 
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        query = "select U.user_id, U.VIP_STATUS, O.order_date, O.total_amount from orders O inner join users U on O.user_id=U.user_id where O.order_id = %s"

        cur.execute(query, (order_id,))

        result = cur.fetchone()

        if not result:
            return None 
        else:
            user_id, VIP_status, order_date, total_amount = result 
            order = {"user_id": user_id, "VIP_status": VIP_status, "order_date": order_date, "total_amount": total_amount}
            return order
    except psycopg2.Error as e:
        print(f"DB Error: {e}")
        return None 

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()    

