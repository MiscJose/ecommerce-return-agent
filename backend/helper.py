import os
import psycopg2

from datetime import date, timedelta

def check_window(order_date, vip_status):
    latest_return_date = None
    if vip_status:
        latest_return_date = order_date + timedelta(days=60)
    else:
        latest_return_date = order_date + timedelta(days=30)

    if date.today() <= latest_return_date:
        return True
    return False

def find_order(order_id):
    conn, cur = None, None 
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        query = "select U.user_id, U.vip_status, O.order_date, O.order_id, O.total_amount from orders O inner join users U on O.user_id=U.user_id where O.order_id = %s"

        cur.execute(query, (order_id,))

        result = cur.fetchone()

        if not result:
            return None 
        else:
            user_id, vip_status, order_date, order_id, total_amount = result 
            order = {"user_id": user_id, "vip_status": vip_status, "order_id": order_id, "order_date": order_date, "total_amount": total_amount}
            return order
    except psycopg2.Error as e:
        print(f"DB Error: {e}")
        return None 

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()    

