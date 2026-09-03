from backend.graph.state import default_return_state
from backend.graph.build_graph import graph


if __name__ == '__main__':

    graph.invoke(
        default_return_state.copy(),
        {"configurable": {"thread_id": "1"}}
    )
