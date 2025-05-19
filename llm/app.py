from Graph.graph import graph_init
from dotenv import load_dotenv

load_dotenv()


def run_graph():
    graph_app=graph_init()
    print(graph_app.get_graph().draw_mermaid())
run_graph()

#async def run_graph(topic: str, success_criteria: str = "Provide accurate information "):
#    """Runs the LangGraph workflow with the specified topic and success criteria."""
#    # Get the compiled Graph
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
#    # Run the Graph
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