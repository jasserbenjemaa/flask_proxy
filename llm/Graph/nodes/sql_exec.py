import os
import json
import re
from typing import Dict, Any, TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from datetime import datetime, timezone
import pytz

from Graph.state import GraphState
from Graph.tools.sql_exec import execute_extracted_sql

load_dotenv()


class SQLExtractorState(TypedDict):
  """State schema for the SQL extractor workflow"""
  flask_code: str
  client_request: Optional[Dict[str, Any]]
  url: Optional[str]
  extracted_sql: str
  integrated_sql: str
  cleaned_sql: str
  error: str


class TimeFunctions:
  """Collection of time-related functions that can be called from Flask code"""

  @staticmethod
  def get_current_time(timezone_str: str = "UTC", format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Get current time in specified timezone and format"""
    try:
      if timezone_str.upper() == "UTC":
        tz = timezone.utc
      else:
        tz = pytz.timezone(timezone_str)

      current_time = datetime.now(tz)
      return current_time.strftime(format_str)
    except Exception as e:
      # Fallback to UTC if timezone parsing fails
      current_time = datetime.now(timezone.utc)
      return current_time.strftime(format_str)

  @staticmethod
  def get_current_timestamp() -> int:
    """Get current Unix timestamp"""
    return int(datetime.now(timezone.utc).timestamp())

  @staticmethod
  def get_current_iso_time() -> str:
    """Get current time in ISO format"""
    return datetime.now(timezone.utc).isoformat()

  @staticmethod
  def get_current_date() -> str:
    """Get current date in YYYY-MM-DD format"""
    return datetime.now(timezone.utc).date().isoformat()


class SQLCleaner:
  """Cleans and sanitizes SQL queries for execution"""

  @staticmethod
  def extract_sql_statements(text: str) -> List[str]:
    """Extract individual SQL statements from text containing multiple queries"""
    # Remove Markdown code blocks
    text = re.sub(r'```sql\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*', '', text)

    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE)

    # Split into potential SQL statements
    statements = []
    current_statement = []

    lines = text.split('\n')
    for line in lines:
      line = line.strip()

      # Skip empty lines and pure comment lines
      if not line or line.startswith('--'):
        continue

      # Remove inline comments but preserve the SQL
      if '--' in line:
        line = line.split('--')[0].strip()
        if not line:
          continue

      current_statement.append(line)

      # End of statement
      if line.endswith(';'):
        stmt = ' '.join(current_statement).strip()
        if stmt and not stmt.startswith('--'):
          statements.append(stmt)
        current_statement = []

    # Handle case where last statement doesn't end with semicolon
    if current_statement:
      stmt = ' '.join(current_statement).strip()
      if stmt and not stmt.startswith('--'):
        statements.append(stmt)

    return statements

  @staticmethod
  def clean_sql_statement(sql: str) -> str:
    """Clean a single SQL statement"""
    # Remove extra whitespace
    sql = ' '.join(sql.split())

    # Ensure proper semicolon ending
    if not sql.endswith(';'):
      sql += ';'

    return sql

  @staticmethod
  def validate_sql_statement(sql: str) -> bool:
    """Basic validation of SQL statement"""
    sql_lower = sql.lower().strip()

    # Check if it starts with a valid SQL keyword
    valid_starts = ['select', 'insert', 'update', 'delete', 'create', 'drop', 'alter', 'with']

    return any(sql_lower.startswith(keyword) for keyword in valid_starts)

  @classmethod
  def clean_and_validate(cls, raw_sql: str) -> Dict[str, Any]:
    """Clean and validate SQL, returning the best executable statement"""
    try:
      statements = cls.extract_sql_statements(raw_sql)

      if not statements:
        return {
          "cleaned_sql": "",
          "error": "No valid SQL statements found",
          "all_statements": []
        }

      cleaned_statements = []
      valid_statements = []

      for stmt in statements:
        cleaned = cls.clean_sql_statement(stmt)
        cleaned_statements.append(cleaned)

        if cls.validate_sql_statement(cleaned):
          valid_statements.append(cleaned)

      # Return the first valid statement for execution
      if valid_statements:
        return {
          "cleaned_sql": valid_statements[0],
          "error": "",
          "all_statements": cleaned_statements,
          "valid_statements": valid_statements
        }
      else:
        return {
          "cleaned_sql": cleaned_statements[0] if cleaned_statements else "",
          "error": "No valid SQL statements found after cleaning",
          "all_statements": cleaned_statements
        }

    except Exception as e:
      return {
        "cleaned_sql": "",
        "error": f"SQL cleaning error: {str(e)}",
        "all_statements": []
      }


class SupabaseCodeAnalyzer:
  """Analyzes Flask + Supabase code using LLM to extract SQL queries"""

  def __init__(self):
    self.llm = ChatGoogleGenerativeAI(
      model="gemini-2.5-flash-preview-04-17",
      google_api_key=os.getenv("GEMINI_API_KEY"),
    )

    self.extraction_prompt = ChatPromptTemplate.from_messages([
      ("system", """Convert Flask + Supabase operations to SQL.

Tasks:
- Convert supabase.table() operations to SQL queries
- Extract table schemas from insert/update operations
- Convert filters (.eq, .neq, etc.) to WHERE clauses
- Convert .order() and .limit() to SQL equivalents
- If you see time-related functions like datetime.now(), get_current_time(), etc., note them for replacement

Output format:
## Database Schema
[CREATE TABLE statements]

## SQL Queries  
[Extracted SQL with brief comments]

Focus only on database operations."""),
      ("human", "Extract SQL from this code:\n\n{flask_code}")
    ])

    self.integration_prompt = ChatPromptTemplate.from_messages([
      ("system", """You are a SQL integration expert. Your task is to merge extracted SQL queries with client request data, URL information, and time functions.

Given:
1. Base SQL queries extracted from Flask code
2. Client request data (JSON format)
3. URL information (if provided)
4. Available time functions and their current values

Your job:
- Integrate the client data into appropriate SQL queries
- Extract parameters from URL (like user_id, resource_id, etc.) - if you need the user_id, you can take it from the URL provided
- Replace placeholders with actual values from client request and URL
- Replace any time-related function calls with actual timestamp values
- Generate clean, executable SQL statements
- Handle INSERT, UPDATE, SELECT operations appropriately
- Maintain data types and constraints
- IMPORTANT: If you need user_id or any ID parameter, extract it from the provided URL path

Available time functions:
- current_time: {current_time}
- current_timestamp: {current_timestamp}
- current_iso_time: {current_iso_time}
- current_date: {current_date}

Return clean, executable SQL statements without markdown formatting."""),
      ("human", """Base SQL Queries:
{extracted_sql}

Client Request Data:
{client_request}

URL Information:
{url}

Please integrate the client data, URL parameters, and time values into the SQL queries. Remember: if you need the user_id, you can take it from the URL provided. Use the provided time values for any datetime operations. Return only clean SQL statements.""")
    ])

  def extract_sql_from_flask(self, flask_code: str) -> str:
    """Use LLM to extract SQL queries from Flask Supabase code"""
    try:
      messages = self.extraction_prompt.format_messages(flask_code=flask_code)
      response = self.llm.invoke(messages)
      return response.content
    except Exception as e:
      return f"Error extracting SQL: {str(e)}"

  def integrate_client_request(self, extracted_sql: str, client_request: Dict[str, Any],
                               url: Optional[str] = None) -> str:
    """Integrate client request data and URL with extracted SQL queries"""
    try:
      # Get current time values
      time_funcs = TimeFunctions()
      current_time = time_funcs.get_current_time()
      current_timestamp = time_funcs.get_current_timestamp()
      current_iso_time = time_funcs.get_current_iso_time()
      current_date = time_funcs.get_current_date()

      client_json = json.dumps(client_request, indent=2)
      messages = self.integration_prompt.format_messages(
        extracted_sql=extracted_sql,
        client_request=client_json,
        url=url or "No URL provided",
        current_time=current_time,
        current_timestamp=current_timestamp,
        current_iso_time=current_iso_time,
        current_date=current_date
      )
      response = self.llm.invoke(messages)
      return response.content
    except Exception as e:
      return f"Error integrating client request: {str(e)}"


# Function execution node
def execute_functions_node(state: SQLExtractorState) -> Dict[str, Any]:
  """Node to execute any required functions like time functions"""
  try:
    flask_code = state.get("flask_code", "")
    functions_result = {}

    # Check if the code needs time-related functions
    time_keywords = ['datetime', 'time', 'now()', 'current_time', 'timestamp']
    needs_time = any(keyword in flask_code.lower() for keyword in time_keywords)

    if needs_time:
      time_funcs = TimeFunctions()
      functions_result.update({
        "current_time": time_funcs.get_current_time(),
        "current_timestamp": time_funcs.get_current_timestamp(),
        "current_iso_time": time_funcs.get_current_iso_time(),
        "current_date": time_funcs.get_current_date(),
        "timezone_info": "UTC"
      })
      print(f"🕒 Time functions executed: {functions_result}")

    return {
      "error": state.get("error")
    }

  except Exception as e:
    return {
      "functions_result": {},
      "error": f"Function execution error: {str(e)}"
    }


# LangGraph Nodes
def extract_sql_node(state: SQLExtractorState) -> Dict[str, Any]:
  """Node to extract SQL queries from Flask Supabase code using LLM"""
  try:
    if not state["flask_code"].strip():
      return {
        "extracted_sql": "",
        "error": "No Flask code provided"
      }

    analyzer = SupabaseCodeAnalyzer()
    extracted_sql = analyzer.extract_sql_from_flask(state["flask_code"])

    return {
      "extracted_sql": extracted_sql,
      "error": ""
    }
  except Exception as e:
    return {
      "extracted_sql": "",
      "error": f"SQL extraction error: {str(e)}"
    }


def integrate_client_request_node(state: SQLExtractorState) -> Dict[str, Any]:
  """Node to integrate client request data with extracted SQL"""
  try:
    # If no client request, just pass through the extracted SQL
    if not state.get("client_request"):
      return {
        "integrated_sql": state["extracted_sql"],
        "error": ""
      }

    analyzer = SupabaseCodeAnalyzer()
    integrated_sql = analyzer.integrate_client_request(
      state["extracted_sql"],
      state["client_request"],
      state.get("url")
    )

    return {
      "integrated_sql": integrated_sql,
      "error": ""
    }
  except Exception as e:
    return {
      "integrated_sql": state["extracted_sql"],
      "error": f"Client request integration error: {str(e)}"
    }


def clean_sql_node(state: SQLExtractorState) -> Dict[str, Any]:
  """Node to clean and validate the integrated SQL"""
  try:
    sql_to_clean = state.get("integrated_sql") or state.get("extracted_sql", "")

    if not sql_to_clean.strip():
      return {
        "cleaned_sql": "",
        "error": "No SQL to clean"
      }

    cleaning_result = SQLCleaner.clean_and_validate(sql_to_clean)

    return {
      "cleaned_sql": cleaning_result["cleaned_sql"],
      "error": cleaning_result["error"]
    }

  except Exception as e:
    return {
      "cleaned_sql": "",
      "error": f"SQL cleaning error: {str(e)}"
    }


def should_continue_extraction(state: SQLExtractorState) -> str:
  """Determine if workflow should continue after SQL extraction"""
  if state["error"]:
    return "error"
  if not state["extracted_sql"].strip():
    return "no_sql"
  return "integrate"


def should_continue_integration(state: SQLExtractorState) -> str:
  """Determine if workflow should continue after integration"""
  if state["error"]:
    return "error"
  return "clean"


def should_continue_cleaning(state: SQLExtractorState) -> str:
  """Determine if workflow should continue after cleaning"""
  if state["error"]:
    return "error"
  return "complete"


# Create the enhanced LangGraph workflow
def create_enhanced_sql_extractor_graph():
  """Create and configure the enhanced SQL extractor workflow graph"""
  workflow = StateGraph(SQLExtractorState)

  # Add nodes
  workflow.add_node("extract_sql", extract_sql_node)
  workflow.add_node("integrate_client_request", integrate_client_request_node)
  workflow.add_node("clean_sql", clean_sql_node)

  # Add edges
  workflow.set_entry_point("extract_sql")

  workflow.add_conditional_edges(
    "extract_sql",
    should_continue_extraction,
    {
      "integrate": "integrate_client_request",
      "error": END,
      "no_sql": END
    }
  )

  workflow.add_conditional_edges(
    "integrate_client_request",
    should_continue_integration,
    {
      "clean": "clean_sql",
      "error": END
    }
  )

  workflow.add_conditional_edges(
    "clean_sql",
    should_continue_cleaning,
    {
      "complete": END,
      "error": END
    }
  )

  return workflow.compile()


# Enhanced usage functions
def process_flask_supabase_code_with_client_request(
    flask_code: str,
    client_request: Optional[Dict[str, Any]] = None,
    url: Optional[str] = None
) -> Dict[str, Any]:
  """Process Flask + Supabase code with optional client request and URL through the enhanced workflow"""
  # Create the workflow
  app = create_enhanced_sql_extractor_graph()

  # Initialize state
  initial_state: SQLExtractorState = {
    "flask_code": flask_code,
    "client_request": client_request,
    "url": url,
    "extracted_sql": "",
    "integrated_sql": "",
    "cleaned_sql": "",
    "error": ""
  }

  # Run the workflow
  result = app.invoke(initial_state)

  return {
    "original_code": result["flask_code"],
    "client_request": result.get("client_request"),
    "url": result.get("url"),
    "extracted_sql": result["extracted_sql"],
    "integrated_sql": result["integrated_sql"],
    "cleaned_sql": result["cleaned_sql"],
    "error": result["error"]
  }


def process_with_client_query(flask_code: str, client_req: Dict[str, Any], url: Optional[str] = None) -> Dict[str, Any]:
  """Convenience function specifically for processing with client queries and URL"""
  return process_flask_supabase_code_with_client_request(flask_code, client_req, url)


def process_without_client_query(flask_code: str, url: Optional[str] = None) -> Dict[str, Any]:
  """Convenience function for processing without client queries but with optional URL"""
  return process_flask_supabase_code_with_client_request(flask_code, None, url)


# Example usage
def sql_exec(state: GraphState) -> Dict[str, Any]:
  sample_flask_supabase_code = state.get("code", "")
  client_request = state.get("client_req", {})
  url = state.get("url", "")

  # Step 0: Execute functions if needed (like time functions)
  functions_state = {"flask_code": sample_flask_supabase_code}
  functions_result = execute_functions_node(functions_state)

  # Step 1: Run your SQL extraction workflow
  result_with_client = process_with_client_query(sample_flask_supabase_code, client_request, url)

  # Step 2: Print the integrated SQL
  print("\n" + "=" * 60)
  print("INTEGRATED SQL WITH CLIENT DATA AND URL:")
  print("=" * 60)
  print(result_with_client['integrated_sql'])

  # Step 2.5: Print the cleaned SQL
  print("\n" + "=" * 60)
  print("CLEANED SQL FOR EXECUTION:")
  print("=" * 60)
  print(result_with_client['cleaned_sql'])

  # Step 3: Execute the cleaned SQL using your executor
  # Modify the result to use cleaned_sql for execution
  execution_result = execute_extracted_sql({
    **result_with_client,
    'integrated_sql': result_with_client['cleaned_sql']  # Use cleaned SQL for execution
  })

  # Step 4: Print execution outcome
  error = None
  print("\n" + "=" * 60)
  print("EXECUTION RESULT")
  print("=" * 60)
  if execution_result["success"]:
    print("✅ Execution successful!")
    print("📦 Data:", execution_result.get("data"))
  else:
    error = execution_result.get("error")
    print("❌ Execution failed:", execution_result["error"])

  # Prepare results
  sql_results = state.get("sqls_result", [])
  if execution_result.get('data'):
    sql_results.append(execution_result.get('data'))

  return {
    "sqls_result": sql_results,
    "funcs_result": functions_result.get("functions_result", {}),
    "error": error,
  }