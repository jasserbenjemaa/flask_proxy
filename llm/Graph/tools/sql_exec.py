import os
import re
from typing import Dict, Any, List, Optional, Union
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import json

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupabaseQueryExecutor:
  """Execute SQL queries on Supabase database using client methods"""

  def __init__(self):
    """Initialize Supabase client"""
    self.supabase_url = os.environ.get('SUPABASE_URL', 'your-supabase-url')
    self.supabase_key = os.environ.get('SUPABASE_KEY', 'your-supabase-anon-key')

    if not self.supabase_url or not self.supabase_key:
      raise ValueError("Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_KEY in your .env file")

    self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
    logger.info("Supabase client initialized successfully")

  def parse_and_execute_sql(self, sql_query: str) -> Dict[str, Any]:
    """
    Parse SQL query and execute using appropriate Supabase method
    This is more reliable than raw SQL execution
    """
    try:
      cleaned_query = self._clean_sql_query(sql_query)
      query_type = self._get_query_type(cleaned_query)

      logger.info(f"Executing {query_type} query: {cleaned_query[:100]}...")

      if query_type == "INSERT":
        return self._execute_parsed_insert(cleaned_query)
      elif query_type == "UPDATE":
        return self._execute_parsed_update(cleaned_query)
      elif query_type == "SELECT":
        return self._execute_parsed_select(cleaned_query)
      elif query_type == "DELETE":
        return self._execute_parsed_delete(cleaned_query)
      else:
        return {
          "success": False,
          "error": f"Unsupported query type: {query_type}",
          "data": None
        }

    except Exception as e:
      logger.error(f"Error parsing and executing SQL: {str(e)}")
      return {
        "success": False,
        "error": f"SQL parsing error: {str(e)}",
        "data": None
      }

  def _clean_sql_query(self, sql_query: str) -> str:
    """Clean and validate SQL query"""
    if not sql_query:
      return ""

    # Remove extra whitespace and comments
    cleaned = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Remove trailing semicolon
    cleaned = cleaned.rstrip(';')

    return cleaned

  def _get_query_type(self, sql_query: str) -> str:
    """Determine the type of SQL query"""
    sql_upper = sql_query.upper().strip()

    if sql_upper.startswith('SELECT'):
      return "SELECT"
    elif sql_upper.startswith('UPDATE'):
      return "UPDATE"
    elif sql_upper.startswith('INSERT'):
      return "INSERT"
    elif sql_upper.startswith('DELETE'):
      return "DELETE"
    else:
      return "UNKNOWN"

  def _execute_parsed_insert(self, sql_query: str) -> Dict[str, Any]:
    """Parse and execute INSERT query"""
    try:
      # Extract table name
      table_match = re.search(r'INSERT\s+INTO\s+(\w+)', sql_query, re.IGNORECASE)
      if not table_match:
        raise ValueError("Could not extract table name from INSERT query")

      table_name = table_match.group(1)

      # Extract columns and values
      columns_match = re.search(r'\(([^)]+)\)\s+VALUES', sql_query, re.IGNORECASE)
      values_match = re.search(r'VALUES\s*\(([^)]+)\)', sql_query, re.IGNORECASE)

      if not columns_match or not values_match:
        raise ValueError("Could not extract columns or values from INSERT query")

      # Parse columns
      columns = [col.strip() for col in columns_match.group(1).split(',')]

      # Parse values - handle different data types
      values_str = values_match.group(1)
      values = self._parse_sql_values(values_str)

      # Create insert data dictionary
      insert_data = {}
      for i, column in enumerate(columns):
        if i < len(values):
          value = values[i]
          # Handle special cases
          if value == 'NOW()' or value == 'CURRENT_TIMESTAMP':
            # Let Supabase handle timestamp
            continue
          insert_data[column] = value

      logger.info(f"Inserting into {table_name}: {insert_data}")

      # Execute using Supabase client
      result = self.supabase.table(table_name).insert(insert_data).execute()

      return {
        "success": True,
        "data": result.data,
        "error": None,
        "rows_inserted": len(result.data) if result.data else 0,
        "query_executed": f"INSERT into {table_name}"
      }

    except Exception as e:
      logger.error(f"Error executing INSERT query: {str(e)}")
      return {
        "success": False,
        "error": str(e),
        "data": None,
        "query_attempted": sql_query
      }

  def _execute_parsed_update(self, sql_query: str) -> Dict[str, Any]:
    """Parse and execute UPDATE query"""
    try:
      # Extract table name
      table_match = re.search(r'UPDATE\s+(\w+)', sql_query, re.IGNORECASE)
      if not table_match:
        raise ValueError("Could not extract table name from UPDATE query")

      table_name = table_match.group(1)

      # Extract SET clause
      set_match = re.search(r'SET\s+(.*?)(?:\s+WHERE|$)', sql_query, re.IGNORECASE | re.DOTALL)
      if not set_match:
        raise ValueError("Could not extract SET clause from UPDATE query")

      set_clause = set_match.group(1)

      # Parse SET values
      update_data = {}
      # Handle both quoted and unquoted values
      set_pairs = re.findall(r"(\w+)\s*=\s*(?:'([^']*)'|(\w+))", set_clause)
      for column, quoted_value, unquoted_value in set_pairs:
        value = quoted_value if quoted_value else unquoted_value
        if column.lower() not in ['updated_at', 'created_at']:  # Skip timestamps
          update_data[column] = value

      # Extract WHERE clause
      where_match = re.search(r'WHERE\s+(.*?)(?:;|$)', sql_query, re.IGNORECASE)
      if not where_match:
        raise ValueError("UPDATE query must have WHERE clause")

      where_clause = where_match.group(1)
      where_pairs = re.findall(r"(\w+)\s*=\s*(?:'([^']*)'|(\w+))", where_clause)

      if not where_pairs:
        raise ValueError("Could not parse WHERE conditions")

      # Execute using Supabase client
      query = self.supabase.table(table_name).update(update_data)

      # Add WHERE conditions
      for column, quoted_value, unquoted_value in where_pairs:
        value = quoted_value if quoted_value else unquoted_value
        query = query.eq(column, value)

      result = query.execute()

      return {
        "success": True,
        "data": result.data,
        "error": None,
        "rows_affected": len(result.data) if result.data else 0,
        "query_executed": f"UPDATE {table_name}"
      }

    except Exception as e:
      logger.error(f"Error executing UPDATE query: {str(e)}")
      return {
        "success": False,
        "error": str(e),
        "data": None,
        "query_attempted": sql_query
      }

  def _execute_parsed_select(self, sql_query: str) -> Dict[str, Any]:
    """Parse and execute SELECT query"""
    try:
      # Extract table name
      from_match = re.search(r'FROM\s+(\w+)', sql_query, re.IGNORECASE)
      if not from_match:
        raise ValueError("Could not extract table name from SELECT query")

      table_name = from_match.group(1)

      # Extract columns
      select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_query, re.IGNORECASE)
      columns = "*"
      if select_match:
        columns_str = select_match.group(1).strip()
        if columns_str != "*":
          columns = columns_str

      # Build query
      query = self.supabase.table(table_name).select(columns)

      # Extract WHERE clause if exists
      where_match = re.search(r'WHERE\s+(.*?)(?:\s+ORDER\s+BY|\s+LIMIT|;|$)', sql_query, re.IGNORECASE)
      if where_match:
        where_clause = where_match.group(1)
        where_pairs = re.findall(r"(\w+)\s*=\s*(?:'([^']*)'|(\w+))", where_clause)

        for column, quoted_value, unquoted_value in where_pairs:
          value = quoted_value if quoted_value else unquoted_value
          query = query.eq(column, value)

      result = query.execute()

      return {
        "success": True,
        "data": result.data,
        "error": None,
        "rows_returned": len(result.data) if result.data else 0,
        "query_executed": f"SELECT from {table_name}"
      }

    except Exception as e:
      logger.error(f"Error executing SELECT query: {str(e)}")
      return {
        "success": False,
        "error": str(e),
        "data": None,
        "query_attempted": sql_query
      }

  def _execute_parsed_delete(self, sql_query: str) -> Dict[str, Any]:
    """Parse and execute DELETE query"""
    try:
      # Extract table name
      from_match = re.search(r'DELETE\s+FROM\s+(\w+)', sql_query, re.IGNORECASE)
      if not from_match:
        raise ValueError("Could not extract table name from DELETE query")

      table_name = from_match.group(1)

      # Extract WHERE clause
      where_match = re.search(r'WHERE\s+(.*?)(?:;|$)', sql_query, re.IGNORECASE)
      if not where_match:
        raise ValueError("DELETE query must have WHERE clause for safety")

      where_clause = where_match.group(1)
      where_pairs = re.findall(r"(\w+)\s*=\s*(?:'([^']*)'|(\w+))", where_clause)

      if not where_pairs:
        raise ValueError("Could not parse WHERE conditions")

      # Build delete query
      query = self.supabase.table(table_name).delete()

      # Add WHERE conditions
      for column, quoted_value, unquoted_value in where_pairs:
        value = quoted_value if quoted_value else unquoted_value
        query = query.eq(column, value)

      result = query.execute()

      return {
        "success": True,
        "data": result.data,
        "error": None,
        "rows_deleted": len(result.data) if result.data else 0,
        "query_executed": f"DELETE from {table_name}"
      }

    except Exception as e:
      logger.error(f"Error executing DELETE query: {str(e)}")
      return {
        "success": False,
        "error": str(e),
        "data": None,
        "query_attempted": sql_query
      }

  def _parse_sql_values(self, values_str: str) -> List[Any]:
    """Parse SQL VALUES clause into Python values"""
    values = []
    # Split by comma, but handle quoted strings
    current_value = ""
    in_quotes = False

    for char in values_str:
      if char == "'" and not in_quotes:
        in_quotes = True
      elif char == "'" and in_quotes:
        in_quotes = False
      elif char == ',' and not in_quotes:
        values.append(self._convert_sql_value(current_value.strip()))
        current_value = ""
        continue

      current_value += char

    # Add the last value
    if current_value.strip():
      values.append(self._convert_sql_value(current_value.strip()))

    return values

  def _convert_sql_value(self, value: str) -> Any:
    """Convert SQL value to appropriate Python type"""
    value = value.strip()

    # Handle quoted strings
    if value.startswith("'") and value.endswith("'"):
      return value[1:-1]  # Remove quotes

    # Handle special SQL functions
    if value.upper() in ['NOW()', 'CURRENT_TIMESTAMP']:
      return 'NOW()'

    # Handle NULL
    if value.upper() == 'NULL':
      return None

    # Try to convert to number
    try:
      if '.' in value:
        return float(value)
      else:
        return int(value)
    except ValueError:
      pass

    # Return as string if all else fails
    return value


# Integration function to work with your SQL extractor
def execute_extracted_sql(extracted_sql_result: Dict[str, Any]) -> Dict[str, Any]:
  """
  Execute the SQL query from your SQL extractor
  """
  try:
    if not extracted_sql_result.get("success", True) or extracted_sql_result.get("error"):
      return {
        "success": False,
        "error": f"SQL extraction failed: {extracted_sql_result.get('error', 'Unknown error')}",
        "data": None
      }

    sql_query = extracted_sql_result.get("integrated_sql", "")
    if not sql_query:
      return {
        "success": False,
        "error": "No SQL query found in extraction result",
        "data": None
      }

    # Execute the query
    executor = SupabaseQueryExecutor()
    result = executor.parse_and_execute_sql(sql_query)

    return {
      "success": result["success"],
      "data": result["data"],
      "error": result["error"],
      "original_extraction": extracted_sql_result,
      "execution_details": result
    }

  except Exception as e:
    logger.error(f"Error in execute_extracted_sql: {str(e)}")
    return {
      "success": False,
      "error": str(e),
      "data": None
    }


# Example usage
if __name__ == "__main__":
  # Test with your INSERT query
  sample_sql = """
    INSERT INTO users (id, name, email, age, created_at, updated_at) 
    VALUES ('a1b2c3d4-e5f6-7890-1234-567890abcdef', 'jasser', 'jasser@gmail.com', 33, NOW(), NOW())
    """

  print("=== Testing Supabase SQL Execution ===")

  try:
    executor = SupabaseQueryExecutor()
    result = executor.parse_and_execute_sql(sample_sql)

    print(f"Success: {result['success']}")
    if result['success']:
      print(f"Data: {result['data']}")
      print(f"Rows inserted: {result.get('rows_inserted', 'N/A')}")
    else:
      print(f"Error: {result['error']}")

  except Exception as e:
    print(f"Failed to initialize or execute: {str(e)}")
    print("\nMake sure you have:")
    print("1. SUPABASE_URL in your .env file")
    print("2. SUPABASE_KEY in your .env file")
    print("3. pip install supabase")