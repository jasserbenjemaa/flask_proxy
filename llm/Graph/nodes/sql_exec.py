import os
from typing import Any, Dict, List

import sqlparse
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from Graph.state import GraphState
# Supabase integration
from supabase import create_client, Client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# SQL operation detection
def detect_sql_operation(query: str) -> str:
  parsed = sqlparse.parse(query)
  if parsed:
    return parsed[0].get_type().lower()
  return "unknown"


def execute_sql(query: str) -> Dict:
  try:
    operation = detect_sql_operation(query)
    if operation == "select":
      response = supabase.rpc("execute_sql", {"query": query}).execute()
    else:
      response = supabase.rpc("execute_sql_mutation", {"query": query}).execute()

    return {"status": "success", "data": response.data, "error": None}
  except Exception as e:
    return {"status": "error", "data": None, "error": f"Query: {query}\nError: {str(e)}"}


class SQLExtractorOutput(BaseModel):
  """Output schema for SQL extraction"""
  sql_query: str = Field(description="The extracted SQL query from the Flask code")
  parameters: List[Any] = Field(default_factory=list, description="List of parameters to be used in the SQL query")
  expected_result_structure: Dict[str, Any] = Field(description="The expected structure of the query result")
  error_detected: bool = Field(description="Whether any errors were detected in the SQL")


def sql_exec(state: GraphState) -> Dict[str, Any]:
  """
  Execute SQL queries extracted from Flask code.
  This node processes SQL code, executes it via Supabase, and returns the results.
  """

  llm = ChatGroq(model="deepseek-r1-distill-llama-70b")

  # Use structured output for SQL extraction
  llm_structured_output = llm.with_structured_output(SQLExtractorOutput)

  # Get the latest SQL snippet from state
  latest_sql_entry = state.get('sqls_result', [])[-1] if state.get('sqls_result', []) else None
  sql_code = latest_sql_entry.get('sql_code', '') if latest_sql_entry else ''

  # Flask code from state
  flask_code = state.get('code', '')

  # System prompt for SQL extraction
  system_prompt = """
    You are a specialized SQL extractor for Flask applications. Your task is to:

    1. Analyze the Flask code and SQL snippet provided
    2. Extract the complete SQL query
    3. Identify all parameters that will be passed to the query
    4. Determine the expected result structure
    5. Check for potential SQL errors or injection vulnerabilities

    Focus specifically on extracting executable SQL that can be run against a database.
    """

  # User prompt template
  user_prompt = """
    ### Flask Code
    ```python
    {flask_code}
    ```

    ### SQL Snippet (preliminary identification)
    ```sql
    {sql_snippet}
    ```

    Please extract the complete SQL query from this code, including any string formatting or parameter substitutions. 

    For example, if the code contains:
    ```python
    cursor.execute("SELECT * FROM users WHERE username = %s AND active = %s", (username, True))
    ```

    You should extract:
    - SQL query: "SELECT * FROM users WHERE username = %s AND active = %s"
    - Parameters: [username, True]
    - Expected result structure: A list of user records with all columns

    If there are multiple SQL queries, focus on the one most relevant to the current operation.
    """

  # Create the prompt
  prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", user_prompt)
  ])

  # Format and invoke the prompt
  formatted_prompt = prompt.format(
    flask_code=flask_code,
    sql_snippet=sql_code
  )

  # Extract SQL details using the LLM
  extraction_result = llm_structured_output.invoke(formatted_prompt)

  # Get the extracted SQL and parameters
  extracted_sql = extraction_result.sql_query
  parameters = extraction_result.parameters

  # Execute the SQL query
  if extracted_sql:
    # For parameterized queries, we would handle parameter substitution here
    # For simplicity, we're executing the raw query
    execution_result = execute_sql(extracted_sql)
  else:
    execution_result = {
      "status": "error",
      "data": None,
      "error": "Failed to extract valid SQL query"
    }

  # Update the state with the execution results
  sqls_result = state.get('sqls_result', [])

  # Update the latest SQL result if it exists
  if sqls_result:
    sqls_result[-1]['result'] = execution_result
    sqls_result[-1]['valid'] = execution_result["status"] == "success"

  # Prepare the new state
  new_state = {
    "sqls_result": sqls_result,
    "the_final_result": {
      "result": execution_result["data"] if execution_result["status"] == "success" else {}
    },
    "error": None if execution_result["status"] == "success" else execution_result["error"]
  }

  return new_state


