from typing import Dict,Any
from Graph.graph import graph_init
from dotenv import load_dotenv

from flask import Flask, jsonify, request
import requests
app = Flask(__name__)

load_dotenv()

from dotenv import dotenv_values
dotenv_vars = dotenv_values(".env")

print(dotenv_vars)

def run_graph(code:str,client_req:Dict[str,Any],url:str):
    initial_state={
        "code":code,
        "client_req":client_req,
        "url":url,
        "supabase_res":{},
        "go_to":"",
        "funcs_result":{} ,#[{result:str,func_code:str,valid:bool}]",
        "sqls_result":{} ,#[{result:str,sql_code:str,valid:bool}]"
        "feedback_on_work":None,
        "the_final_result":None, #initial state {"result":{}}"
        "error":None,
    }
    graph_app=graph_init()
    result=graph_app.invoke(initial_state)
    #print(graph_app.get_graph().draw_mermaid())
    return result

@app.route('/llm',methods=["POST"])
def llm():
    data = request.get_json()
    code=data.get("code","")
    client_req=data.get("client_req",{})
    url=data.get("url","")
    run_graph(code, client_req,url)
    return 
    
@app.route('/',methods=["POST"])
def home():
    data = request.get_json()
    return data
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)
