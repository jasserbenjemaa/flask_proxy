from Graph.graph import graph_init
from dotenv import load_dotenv

load_dotenv()

from dotenv import dotenv_values
# This returns a dict of only the .env file variables
dotenv_vars = dotenv_values(".env")

print(dotenv_vars)

def run_graph():
    graph_app=graph_init()
    print(graph_app.get_graph().draw_mermaid())
run_graph()
