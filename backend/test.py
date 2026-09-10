from graph.state import default_return_state
from graph.build_graph import graph

from helper import find_order, check_window
from datetime import datetime

# DATABASE_URL="postgresql://admin:password@localhost:5432/ecommerce_db" python test.py



if __name__ == '__main__':

    order = find_order(1)
    print(check_window(order['order_date'], True))

    # find_order("banana")

    # graph.invoke(
    #     default_return_state.copy(),
    #     {"configurable": {"thread_id": "1"}}
    # )
