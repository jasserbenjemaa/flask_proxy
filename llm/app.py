from flask import Flask
from graph.graph import run_agent

from langchain_core.messages import HumanMessage
from graph.graph import graph_init
from dotenv import load_dotenv
from IPython.display import Image,display

load_dotenv()

app = Flask(__name__)

def run_graph():
    graph_app=graph_init()
    display(Image(graph_app.draw_mermaid_png()))

#async def run_graph(topic: str, success_criteria: str = "Provide accurate information "):
#    """Runs the LangGraph workflow with the specified topic and success criteria."""
#    # Get the compiled graph
#    app, browser, playwright = await graph_init()
#
#    # Initialize state with user message
#    initial_state = {
#        "messages": [HumanMessage(content=topic)],
#        "human_message": topic,
#        "feedback_on_work": None,
#        "success_criteria": success_criteria,
#        "success_criteria_met": False,
#        "user_input_needed": False
#    }
#
#    # Run the graph
#    final_state = await app.ainvoke(initial_state)
#
#    # Print the final messages
#    print("\n=== CONVERSATION HISTORY ===")
#    for msg in final_state["messages"]:
#        if isinstance(msg, HumanMessage):
#            print(f"human: {msg.content}")
#        elif isinstance(msg, AIMessage):
#            print(f"ai: {msg.content}")
#
#    print("\n=== SUCCESS CRITERIA MET ===")
#    print(final_state["success_criteria_met"])
#    await browser.close()
#
#    return final_state


@app.route('/llm')
def home():
    run_agent()
    return "Hello, Flask!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8008)
