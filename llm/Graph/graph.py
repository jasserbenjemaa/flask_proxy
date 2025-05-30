from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from Graph.state import GraphState
from Graph.nodes.evaluation import evaluation
from Graph.nodes.function_exec import func_exec
from Graph.nodes.planer import planer
from Graph.nodes.sql_exec import sql_exec
from Graph.const import SQL_EXEC,FUNC_EXEC,PLANER,EVALUATOR
from Graph.routers.planer_router import planer_router
from Graph.routers.evaluator_router import evaluator_router

def graph_init():
    graph_builder=StateGraph(GraphState)

    graph_builder.add_node(EVALUATOR,evaluation)
    graph_builder.add_node(FUNC_EXEC,func_exec)
    graph_builder.add_node(SQL_EXEC,sql_exec)
    graph_builder.add_node(PLANER,planer)

    graph_builder.set_entry_point(PLANER)
    graph_builder.add_edge(FUNC_EXEC,EVALUATOR)
    graph_builder.add_edge(SQL_EXEC,EVALUATOR)


    graph_builder.add_conditional_edges(EVALUATOR,evaluator_router,{
        FUNC_EXEC:FUNC_EXEC,
        SQL_EXEC:SQL_EXEC,
        PLANER:PLANER
    })

    graph_builder.add_conditional_edges(PLANER,planer_router,{
        SQL_EXEC:SQL_EXEC,
        "END":END,
        FUNC_EXEC:FUNC_EXEC,
    })

    return graph_builder.compile()

