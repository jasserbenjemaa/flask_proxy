from typing import  Any, Optional, Dict,List
from langgraph.graph import add_messages
from typing_extensions import TypedDict, Annotated


class GraphState(TypedDict):
    """
    Represent the state of our Graph

    Attributes:
        code:flask code
        client_req:client request
        go_to:go to the sql_exec or func_exec
        funcs_result: dict contains all function results
        sqls_result: dict contains all sql results
        feedback_on_work:feedback on the assistant's response
        the_final_result:the result of the code
    """

    code:str
    client_req:str
    go_to:str
    funcs_result: List[Dict[str, Any]]#[{result:str,func_code:str,valid:bool}]
    sqls_result: List[Dict[str, Any]]#[{result:str,sql_code:str,valid:bool}]
    feedback_on_work:Optional[str]
    the_final_result:Dict[str,Any] #initial state {"result":{}}
    error:Optional[str]

