from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from graph.tools import tools
from graph.state import GraphState
from graph.nodes import evaluation
from graph.nodes import function_exec
from graph.nodes import planer
from graph.nodes import sql_exec
from graph.const import SQL_EXEC,FUNC_EXEC,PLANER,EVALUATOR
from graph.routers.planer_router import planer_router
from graph.routers.sql_router import sql_router
from graph.routers.evaluator_router import evaluator_router


def graph_init():
    graph_builder=StateGraph(GraphState)

    graph_builder.add_node(EVALUATOR,evaluation)
    graph_builder.add_node(FUNC_EXEC,function_exec)
    graph_builder.add_node(SQL_EXEC,sql_exec)
    graph_builder.add_node(PLANER,planer)
    graph_builder.add_node("tools", ToolNode(tools=tools))

    graph_builder.add_edge(FUNC_EXEC,EVALUATOR)
    graph_builder.add_edge(SQL_EXEC,EVALUATOR)

    graph_builder.add_edge(SQL_EXEC,"tools")
    graph_builder.add_conditional_edges(SQL_EXEC,sql_router,{"tools":"tools",EVALUATOR:EVALUATOR})

    graph_builder.add_conditional_edges(EVALUATOR,evaluator_router,{SQL_EXEC:SQL_EXEC,PLANER:PLANER})
    graph_builder.add_conditional_edges(EVALUATOR,evaluator_router,{FUNC_EXEC:FUNC_EXEC,PLANER:PLANER})

    graph_builder.add_conditional_edges(EVALUATOR,evaluator_router,{SQL_EXEC:SQL_EXEC,'END':'END'})
    graph_builder.add_conditional_edges(EVALUATOR,evaluator_router,{FUNC_EXEC:FUNC_EXEC,'END':'END'})

    graph_builder.add_conditional_edges(PLANER,planer_router,{SQL_EXEC:SQL_EXEC,"END":END})
    graph_builder.add_conditional_edges(PLANER,planer_router,{FUNC_EXEC:FUNC_EXEC,"END":END})
    graph_builder.add_conditional_edges(PLANER,planer_router,{EVALUATOR:EVALUATOR,"END":END})

    return graph_builder.compile()

