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

# NOTE: You need to ensure these imports exist in your project structure
try:
  from Graph.state import GraphState
  from Graph.tools.sql_exec import execute_extracted_sql
except ImportError as e:
  print(f"Warning: Import error - {e}")
  print("Please ensure Graph.state and Graph.tools.sql_exec modules exist")
  # Define fallback types if needed
  GraphState = Dict[str, Any]

  def execute_extracted_sql(result: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback function - replace with your actual implementation"""
    return {"success": False, "error": "execute_extracted_sql not implemented"}

load_dotenv()


class SQLExtractorState(TypedDict):
  """State schema for the SQL extractor workflow"""
  flask_code: str
  table_name: str
  client_request: Optional[Dict[str, Any]]
  url: Optional[str]
  extracted_sql: str
  integrated_sql: str
  cleaned_sql_statements: List[str]
  all_sql_results: List[Dict[str, Any]]
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


class EnhancedSQLCleaner:
  """Enhanced SQL cleaner that handles multiple statements properly"""

  @staticmethod
  def extract_sql_statements(text: str) -> List[str]:
    """Extract individual SQL statements from text containing multiple queries"""
    # Remove Markdown code blocks
    text = re.sub(r'```sql\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*', '', text)
    text = re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE)

    statements = []
    current_statement = []
    in_string = False
    quote_char = None

    lines = text.split('\n')
    for line in lines:
      line = line.strip()

      if not line or line.startswith('--'):
        continue

      if line.lower() in ['users', 'posts', 'comments', 'orders', 'products']:
        continue

      cleaned_line = ""
      i = 0
      while i < len(line):
        char = line[i]

        if not in_string and char in ["'", '"']:
          in_string = True
          quote_char = char
          cleaned_line += char
        elif in_string and char == quote_char:
          if i + 1 < len(line) and line[i + 1] == quote_char:
            cleaned_line += char + char
            i += 1
          else:
            in_string = False
            quote_char = None
            cleaned_line += char
        elif not in_string and char == '-' and i + 1 < len(line) and line[i + 1] == '-':
          break
        else:
          cleaned_line += char
        i += 1

      line = cleaned_line.strip()
      if not line:
        continue

      current_statement.append(line)

      if line.endswith(';'):
        stmt = ' '.join(current_statement).strip()
        if stmt and not stmt.startswith('--'):
          statements.append(stmt)
        current_statement = []

    if current_statement:
      stmt = ' '.join(current_statement).strip()
      if stmt and not stmt.startswith('--'):
        statements.append(stmt)

    return statements

  @staticmethod
  def clean_sql_statement(sql: str) -> str:
    """Clean a single SQL statement"""
    sql = ' '.join(sql.split())
    if not sql.endswith(';'):
      sql += ';'
    return sql

  @staticmethod
  def validate_sql_statement(sql: str) -> bool:
    """Basic validation of SQL statement"""
    sql_lower = sql.lower().strip()
    valid_starts = ['select', 'insert', 'update', 'delete', 'create', 'drop', 'alter', 'with']
    return any(sql_lower.startswith(keyword) for keyword in valid_starts)

  @classmethod
  def clean_and_validate_all(cls, raw_sql: str) -> Dict[str, Any]:
    """Clean and validate ALL SQL statements, returning all valid ones"""
    try:
      statements = cls.extract_sql_statements(raw_sql)

      if not statements:
        return {
          "cleaned_sql_statements": [],
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

      return {
        "cleaned_sql_statements": valid_statements,
        "error": "" if valid_statements else "No valid SQL statements found after cleaning",
        "all_statements": cleaned_statements,
        "valid_statements": valid_statements
      }

    except Exception as e:
      return {
        "cleaned_sql_statements": [],
        "error": f"SQL cleaning error: {str(e)}",
        "all_statements": []
      }


class SupabaseCodeAnalyzer:
  """Analyzes Flask + Supabase code using LLM to extract SQL queries"""

  def __init__(self):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
      raise ValueError("GEMINI_API_KEY environment variable is required")

    self.llm = ChatGoogleGenerativeAI(
      model="gemini-2.5-flash-preview-04-17",
      google_api_key=api_key,
    )

    # OPTIMIZED EXTRACTION PROMPT - Much shorter and more direct
    self.extraction_prompt = ChatPromptTemplate.from_messages([
      ("system", """Convert Flask + Supabase code to SQL.

Extract:
- supabase.table() → SQL queries
- .eq(), .neq(), .filter() → WHERE clauses  
- .order(), .limit() → ORDER BY, LIMIT
- insert/update operations → INSERT/UPDATE statements
- Time functions → note for replacement

Output format:
## Schema
[CREATE TABLE if needed]

## SQL
[All SQL statements in execution order]"""),
      ("human", "Code:\n{flask_code}")
    ])

    # OPTIMIZED INTEGRATION PROMPT - Much more concise
    self.integration_prompt = ChatPromptTemplate.from_messages([
      ("system", """Merge SQL with client data and URL parameters.

Tasks:
- Replace placeholders with actual values from client_request
- Extract IDs from URL path (e.g., /users/123 → user_id=123)
- Use provided timestamps for datetime operations
- Return ALL executable SQL statements

Time values:
- current_time: {current_time}
- current_timestamp: {current_timestamp}
- current_iso_time: {current_iso_time}
- current_date: {current_date}
- table: {table_name}

Return clean SQL statements without markdown, each ending with semicolon."""),
      ("human", """SQL: {extracted_sql}
Client Data: {client_request}
URL: {url}

Integrate all data and return executable SQL statements.""")
    ])

  def extract_sql_from_flask(self, flask_code: str) -> str:
    """Use LLM to extract SQL queries from Flask Supabase code"""
    try:
      if not flask_code.strip():
        return "Error: No Flask code provided"

      messages = self.extraction_prompt.format_messages(flask_code=flask_code)
      response = self.llm.invoke(messages)

      if not response or not hasattr(response, 'content'):
        return "Error: Invalid response from LLM"

      return response.content
    except Exception as e:
      return f"Error extracting SQL: {str(e)}"

  def integrate_client_request(self, extracted_sql: str, client_request: Dict[str, Any],
                               url: Optional[str] = None, table_name: str = "") -> str:
    """Integrate client request data and URL with extracted SQL queries"""
    try:
      if not extracted_sql.strip():
        return "Error: No extracted SQL provided"

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
        table_name=table_name,
        current_time=current_time,
        current_timestamp=current_timestamp,
        current_iso_time=current_iso_time,
        current_date=current_date
      )
      response = self.llm.invoke(messages)

      if not response or not hasattr(response, 'content'):
        return "Error: Invalid response from LLM during integration"

      return response.content
    except Exception as e:
      return f"Error integrating client request: {str(e)}"


def execute_functions_node(state: SQLExtractorState) -> Dict[str, Any]:
  """Node to execute any required functions like time functions"""
  try:
    flask_code = state.get("flask_code", "")
    functions_result = {}

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
      "functions_result": functions_result,
      "error": state.get("error", "")
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
    if not state.get("flask_code", "").strip():
      return {
        "extracted_sql": "",
        "error": "No Flask code provided"
      }

    analyzer = SupabaseCodeAnalyzer()
    extracted_sql = analyzer.extract_sql_from_flask(state["flask_code"])

    if extracted_sql.startswith("Error"):
      return {
        "extracted_sql": "",
        "error": extracted_sql
      }

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
    if not state.get("client_request"):
      return {
        "integrated_sql": state.get("extracted_sql", ""),
        "error": ""
      }

    extracted_sql = state.get("extracted_sql", "")
    if not extracted_sql.strip():
      return {
        "integrated_sql": "",
        "error": "No extracted SQL to integrate"
      }

    analyzer = SupabaseCodeAnalyzer()
    integrated_sql = analyzer.integrate_client_request(
      extracted_sql,
      state.get("client_request", {}),
      state.get("url"),
      state.get("table_name", "")
    )

    if integrated_sql.startswith("Error"):
      return {
        "integrated_sql": state.get("extracted_sql", ""),
        "error": integrated_sql
      }

    return {
      "integrated_sql": integrated_sql,
      "error": ""
    }
  except Exception as e:
    return {
      "integrated_sql": state.get("extracted_sql", ""),
      "error": f"Client request integration error: {str(e)}"
    }


def clean_sql_node(state: SQLExtractorState) -> Dict[str, Any]:
  """Node to clean and validate ALL integrated SQL statements"""
  try:
    sql_to_clean = state.get("integrated_sql") or state.get("extracted_sql", "")

    if not sql_to_clean.strip():
      return {
        "cleaned_sql_statements": [],
        "error": "No SQL to clean"
      }

    cleaning_result = EnhancedSQLCleaner.clean_and_validate_all(sql_to_clean)

    return {
      "cleaned_sql_statements": cleaning_result["cleaned_sql_statements"],
      "error": cleaning_result["error"]
    }

  except Exception as e:
    return {
      "cleaned_sql_statements": [],
      "error": f"SQL cleaning error: {str(e)}"
    }


def execute_all_sql_node(state: SQLExtractorState) -> Dict[str, Any]:
  """Node to execute ALL SQL statements sequentially"""
  try:
    sql_statements = state.get("cleaned_sql_statements", [])

    if not sql_statements:
      return {
        "all_sql_results": [],
        "error": "No SQL statements to execute"
      }

    all_results = []
    print(f"\n🚀 Executing {len(sql_statements)} SQL statements...")

    for i, sql_statement in enumerate(sql_statements, 1):
      print(f"\n📋 Statement {i}: {sql_statement}")

      try:
        statement_result = {
          "statement_number": i,
          "sql": sql_statement,
          "integrated_sql": sql_statement
        }

        execution_result = execute_extracted_sql(statement_result)
        execution_result["statement_number"] = i
        execution_result["original_sql"] = sql_statement
        all_results.append(execution_result)

        if execution_result.get("success"):
          print(f"✅ Statement {i} succeeded!")
          if execution_result.get("data"):
            print(f"📦 Data: {execution_result.get('data')}")
        else:
          print(f"❌ Statement {i} failed: {execution_result.get('error')}")

      except Exception as e:
        error_result = {
          "statement_number": i,
          "original_sql": sql_statement,
          "success": False,
          "error": f"Execution error: {str(e)}",
          "data": None
        }
        all_results.append(error_result)
        print(f"❌ Statement {i} exception: {str(e)}")

    successful = sum(1 for r in all_results if r.get('success'))
    failed = len(all_results) - successful
    print(f"\n🏁 Complete: ✅{successful} ❌{failed}")

    return {
      "all_sql_results": all_results,
      "error": ""
    }

  except Exception as e:
    return {
      "all_sql_results": [],
      "error": f"SQL execution error: {str(e)}"
    }


# Conditional functions
def should_continue_extraction(state: SQLExtractorState) -> str:
  if state.get("error"):
    return "error"
  if not state.get("extracted_sql", "").strip():
    return "no_sql"
  return "integrate"


def should_continue_integration(state: SQLExtractorState) -> str:
  if state.get("error"):
    return "error"
  return "clean"


def should_continue_cleaning(state: SQLExtractorState) -> str:
  if state.get("error"):
    return "error"
  if not state.get("cleaned_sql_statements"):
    return "no_clean_sql"
  return "execute"


def should_continue_execution(state: SQLExtractorState) -> str:
  return "complete"


# Create the workflow graph
def create_enhanced_sql_extractor_graph():
  """Create and configure the enhanced SQL extractor workflow graph"""
  workflow = StateGraph(SQLExtractorState)

  # Add nodes
  workflow.add_node("extract_sql", extract_sql_node)
  workflow.add_node("integrate_client_request", integrate_client_request_node)
  workflow.add_node("clean_sql", clean_sql_node)
  workflow.add_node("execute_all_sql", execute_all_sql_node)

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
      "execute": "execute_all_sql",
      "error": END,
      "no_clean_sql": END
    }
  )

  workflow.add_conditional_edges(
    "execute_all_sql",
    should_continue_execution,
    {
      "complete": END
    }
  )

  return workflow.compile()


# Main processing functions
def process_flask_supabase_code_with_client_request(
    flask_code: str,
    table_name: str,
    client_request: Optional[Dict[str, Any]] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
  """Process Flask + Supabase code with optional client request and URL"""
  try:
    app = create_enhanced_sql_extractor_graph()

    initial_state: SQLExtractorState = {
      "flask_code": flask_code,
      "client_request": client_request,
      "table_name": table_name,
      "url": url,
      "extracted_sql": "",
      "integrated_sql": "",
      "cleaned_sql_statements": [],
      "all_sql_results": [],
      "error": ""
    }

    result = app.invoke(initial_state)

    return {
      "original_code": result["flask_code"],
      "client_request": result.get("client_request"),
      "url": result.get("url"),
      "extracted_sql": result["extracted_sql"],
      "integrated_sql": result["integrated_sql"],
      "cleaned_sql_statements": result["cleaned_sql_statements"],
      "all_sql_results": result["all_sql_results"],
      "error": result["error"]
    }
  except Exception as e:
    return {
      "original_code": flask_code,
      "client_request": client_request,
      "url": url,
      "extracted_sql": "",
      "integrated_sql": "",
      "cleaned_sql_statements": [],
      "all_sql_results": [],
      "error": f"Workflow execution error: {str(e)}"
    }


def process_with_client_query(flask_code: str, table_name: str, client_req: Dict[str, Any],
                              url: Optional[str] = None) -> Dict[str, Any]:
  """Convenience function for processing with client queries and URL"""
  return process_flask_supabase_code_with_client_request(flask_code, table_name, client_req, url)


def process_without_client_query(flask_code: str, table_name: str, url: Optional[str] = None) -> Dict[str, Any]:
  """Convenience function for processing without client queries"""
  return process_flask_supabase_code_with_client_request(flask_code, table_name, None, url)


# Main execution function
def sql_exec(state: GraphState) -> Dict[str, Any]:
  """Main execution function for the SQL extraction and execution pipeline"""
  sample_flask_supabase_code = state.get("code", "")
  client_request = state.get("client_req", {})
  url = state.get("url", "")
  table_name = state.get("table_name", "")

  if not sample_flask_supabase_code.strip():
    return {
      "sqls_result": state.get("sqls_result", []),
      "funcs_result": {},
      "error": "No Flask code provided"
    }

  # Execute time functions if needed
  functions_state: SQLExtractorState = {
    "flask_code": sample_flask_supabase_code,
    "table_name": table_name,
    "client_request": client_request,
    "url": url,
    "extracted_sql": "",
    "integrated_sql": "",
    "cleaned_sql_statements": [],
    "all_sql_results": [],
    "error": ""
  }
  functions_result = execute_functions_node(functions_state)

  try:
    # Run the SQL extraction workflow
    result_with_client = process_with_client_query(sample_flask_supabase_code, table_name, client_request, url)

    if result_with_client.get('error'):
      return {
        "sqls_result": state.get("sqls_result", []),
        "funcs_result": functions_result.get("functions_result", {}),
        "error": result_with_client['error']
      }

    # Print results
    print("\n" + "=" * 50)
    print("INTEGRATED SQL:")
    print("=" * 50)
    print(result_with_client.get('integrated_sql', 'None'))

    print("\n" + "=" * 50)
    print("CLEANED SQL STATEMENTS:")
    print("=" * 50)
    cleaned_statements = result_with_client.get('cleaned_sql_statements', [])
    for i, stmt in enumerate(cleaned_statements, 1):
      print(f"{i}. {stmt}")

    # Get and process execution results
    all_sql_results = result_with_client.get('all_sql_results', [])

    print("\n" + "=" * 50)
    print("EXECUTION RESULTS:")
    print("=" * 50)

    if all_sql_results:
      successful_results = [r for r in all_sql_results if r.get("success")]
      failed_results = [r for r in all_sql_results if not r.get("success")]

      for result in all_sql_results:
        status = "✅ SUCCESS" if result.get("success") else "❌ FAILED"
        print(f"Statement {result.get('statement_number', '?')}: {status}")
        if result.get("data"):
          print(f"   📦 Data: {result.get('data')}")
        if result.get("error"):
          print(f"   💥 Error: {result.get('error')}")

      print(f"\n📊 Summary: {len(successful_results)} successful, {len(failed_results)} failed")

      # Prepare results
      sql_results = state.get("sqls_result", [])
      for result in successful_results:
        if result.get('data'):
          sql_results.append(result.get('data'))

      error = None
      if failed_results:
        error = f"Some SQL statements failed: {'; '.join([r.get('error', 'Unknown') for r in failed_results])}"

      return {
        "sqls_result": sql_results,
        "funcs_result": functions_result.get("functions_result", {}),
        "all_sql_results": all_sql_results,
        "error": error,
      }
    else:
      print("❌ No SQL statements executed")
      return {
        "sqls_result": state.get("sqls_result", []),
        "funcs_result": functions_result.get("functions_result", {}),
        "all_sql_results": [],
        "error": "No SQL statements executed"
      }

  except Exception as e:
    return {
      "sqls_result": state.get("sqls_result", []),
      "funcs_result": functions_result.get("functions_result", {}),
      "all_sql_results": [],
      "error": f"Unexpected error: {str(e)}"
    }