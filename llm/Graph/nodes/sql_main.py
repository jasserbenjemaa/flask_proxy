import os
import json
import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import logging

load_dotenv()


@dataclass
class QueryResult:
  """Data class to hold query execution results"""
  query_id: str
  sql: str
  success: bool
  data: Optional[Any] = None
  error: Optional[str] = None
  execution_time: float = 0.0
  timestamp: str = ""
  operation: str = ""
  rows_affected: int = 0


class SQLBatchExecutor:
  """Execute SQL queries in batch and return structured results"""

  def __init__(self, connection_config: Optional[Dict[str, str]] = None):
    # Initialize logging
    logging.basicConfig(level=logging.INFO)
    self.logger = logging.getLogger(__name__)

    # Initialize Supabase connection
    if connection_config:
      self.supabase = create_client(
        connection_config['url'],
        connection_config['key']
      )
    elif os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
      self.supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
      )
    else:
      self.supabase = None
      self.logger.warning("No Supabase configuration found. Execution will be disabled.")

  def execute_single_query(self, sql_info: Dict[str, Any], query_id: str = None) -> QueryResult:
    """Execute a single SQL query and return structured result"""
    if query_id is None:
      query_id = f"query_{int(time.time() * 1000)}"

    start_time = time.time()
    timestamp = datetime.now().isoformat()

    # Initialize result object
    result = QueryResult(
      query_id=query_id,
      sql=sql_info.get('sql', ''),
      success=False,
      timestamp=timestamp,
      operation=sql_info.get('operation', 'UNKNOWN')
    )

    if not self.supabase:
      result.error = "Supabase connection not configured"
      result.execution_time = time.time() - start_time
      return result

    try:
      sql = sql_info['sql']
      table_name = sql_info.get('table_name', '')
      operation = sql_info.get('operation', '').upper()

      # Determine operation from SQL if not provided
      if not operation:
        sql_upper = sql.upper().strip()
        if sql_upper.startswith('SELECT'):
          operation = 'SELECT'
        elif sql_upper.startswith('INSERT'):
          operation = 'INSERT'
        elif sql_upper.startswith('UPDATE'):
          operation = 'UPDATE'
        elif sql_upper.startswith('DELETE'):
          operation = 'DELETE'
        else:
          operation = 'UNKNOWN'

      result.operation = operation

      # Execute based on operation type
      if operation == 'SELECT' or operation == 'GET':
        data = self._execute_select(sql_info)
      elif operation == 'INSERT' or operation == 'POST':
        data = self._execute_insert(sql_info)
      elif operation == 'UPDATE' or operation == 'PUT':
        data = self._execute_update(sql_info)
      elif operation == 'DELETE':
        data = self._execute_delete(sql_info)
      else:
        raise ValueError(f"Unsupported operation: {operation}")

      result.success = True
      result.data = data.data if hasattr(data, 'data') else data
      result.rows_affected = len(result.data) if result.data else 0

    except Exception as e:
      result.error = str(e)
      self.logger.error(f"Error executing query {query_id}: {e}")

    result.execution_time = time.time() - start_time
    return result

  def _execute_select(self, sql_info: Dict[str, Any]):
    """Execute SELECT operation"""
    table_name = sql_info['table_name']
    url_info = sql_info.get('url_info', {})
    parameters = sql_info.get('parameters', {})

    query = self.supabase.table(table_name).select('*')

    # Apply filters based on URL and parameters
    resource_id = url_info.get('resource_id')
    if resource_id:
      query = query.eq('id', resource_id)

    # Apply query parameters
    if 'limit' in parameters:
      query = query.limit(int(parameters['limit']))
    if 'offset' in parameters:
      query = query.offset(int(parameters['offset']))

    # Apply additional filters from parameters
    for key, value in parameters.items():
      if key not in ['limit', 'offset', 'id'] and value is not None:
        query = query.eq(key, value)

    return query.execute()

  def _execute_insert(self, sql_info: Dict[str, Any]):
    """Execute INSERT operation"""
    table_name = sql_info['table_name']

    # Extract data from SQL or parameters
    data = self._extract_insert_data_from_sql(sql_info['sql'])

    # If no data found in SQL, try to get it from parameters or request
    if not data:
      # Try to get data from the original request if available
      original_request = sql_info.get('request', {})
      data = original_request.get('data', original_request.get('body', {}))

    if not data:
      raise ValueError("No data found for INSERT operation")

    return self.supabase.table(table_name).insert(data).execute()

  def _execute_update(self, sql_info: Dict[str, Any]):
    """Execute UPDATE operation"""
    table_name = sql_info['table_name']
    url_info = sql_info.get('url_info', {})

    # Extract update data from SQL
    data = self._extract_update_data_from_sql(sql_info['sql'])

    if not data:
      # Try to get data from the original request
      original_request = sql_info.get('request', {})
      data = original_request.get('data', original_request.get('body', {}))

    if not data:
      raise ValueError("No data found for UPDATE operation")

    query = self.supabase.table(table_name).update(data)

    # Apply WHERE conditions
    resource_id = url_info.get('resource_id')
    if resource_id:
      query = query.eq('id', resource_id)

    return query.execute()

  def _execute_delete(self, sql_info: Dict[str, Any]):
    """Execute DELETE operation"""
    table_name = sql_info['table_name']
    url_info = sql_info.get('url_info', {})

    query = self.supabase.table(table_name).delete()

    # Apply WHERE conditions
    resource_id = url_info.get('resource_id')
    if resource_id:
      query = query.eq('id', resource_id)
    else:
      # Safety check - don't allow DELETE without conditions
      raise ValueError("DELETE operation requires resource ID for safety")

    return query.execute()

  def _extract_insert_data_from_sql(self, sql: str) -> Dict[str, Any]:
    """Extract data from INSERT SQL statement"""
    import re

    # Simple regex to extract INSERT data
    match = re.search(r'INSERT INTO \w+ \(([^)]+)\) VALUES \(([^)]+)\)', sql, re.IGNORECASE)
    if match:
      columns = [col.strip().strip("'\"") for col in match.group(1).split(',')]
      values = [val.strip().strip("'\"") for val in match.group(2).split(',')]
      return dict(zip(columns, values))

    return {}

  def _extract_update_data_from_sql(self, sql: str) -> Dict[str, Any]:
    """Extract data from UPDATE SQL statement"""
    import re

    # Simple regex to extract UPDATE data
    match = re.search(r'SET (.+?) WHERE', sql, re.IGNORECASE)
    if match:
      updates = {}
      for update in match.group(1).split(','):
        if '=' in update:
          key, value = update.split('=', 1)
          updates[key.strip()] = value.strip().strip("'\"")
      return updates

    return {}

  def execute_batch(self, sql_queries: List[Dict[str, Any]],
                    continue_on_error: bool = True,
                    max_retries: int = 0,
                    delay_between_queries: float = 0.0) -> Dict[str, Any]:
    """Execute multiple SQL queries and return batch results"""


    results = []
    successful_count = 0
    failed_count = 0
    total_execution_time = 0.0

    start_time = time.time()

    for i, sql_info in enumerate(sql_queries):
      query_id = f"batch_query_{i + 1}"

      # Add delay between queries if specified
      if delay_between_queries > 0 and i > 0:
        time.sleep(delay_between_queries)

      # Execute query with retries
      result = self._execute_with_retry(sql_info, query_id, max_retries)
      results.append(result)

      total_execution_time += result.execution_time

      if result.success:
        successful_count += 1
      else:
        failed_count += 1
        self.logger.error(f"❌ Query {i + 1}/{len(sql_queries)} failed: {result.error}")

        if not continue_on_error:
          self.logger.error("Stopping batch execution due to error")
          break

    batch_execution_time = time.time() - start_time

    # Prepare summary
    summary = {
      "total_queries": len(sql_queries),
      "successful_queries": successful_count,
      "failed_queries": failed_count,
      "success_rate": (successful_count / len(sql_queries)) * 100 if sql_queries else 0,
      "total_execution_time": batch_execution_time,
      "average_query_time": total_execution_time / len(sql_queries) if sql_queries else 0,
      "timestamp": datetime.now().isoformat(),
      "continue_on_error": continue_on_error,
      "max_retries": max_retries
    }


    return {
      "summary": summary,
      "results": [self._result_to_dict(result) for result in results],
      "success": failed_count == 0
    }

  def _execute_with_retry(self, sql_info: Dict[str, Any], query_id: str, max_retries: int) -> QueryResult:
    """Execute query with retry logic"""
    for attempt in range(max_retries + 1):
      result = self.execute_single_query(sql_info, f"{query_id}_attempt_{attempt + 1}")

      if result.success or attempt == max_retries:
        return result

      self.logger.warning(f"Query {query_id} failed (attempt {attempt + 1}/{max_retries + 1}): {result.error}")
      if attempt < max_retries:
        time.sleep(1 * (attempt + 1))  # Exponential backoff

    return result

  def _result_to_dict(self, result: QueryResult) -> Dict[str, Any]:
    """Convert QueryResult to dictionary"""
    return {
      "query_id": result.query_id,
      "sql": result.sql,
      "success": result.success,
      "data": result.data,
      "error": result.error,
      "execution_time": result.execution_time,
      "timestamp": result.timestamp,
      "operation": result.operation,
      "rows_affected": result.rows_affected
    }

  def execute_from_integrator_output(self, integrator_results: List[Dict[str, Any]],
                                     execute_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute SQL queries from SQLQueryIntegrator output"""
    if execute_params is None:
      execute_params = {}

    # Extract sql_info from integrator results
    sql_queries = []
    for result in integrator_results:
      if 'sql_info' in result:
        # Add additional context from the integrator result
        sql_info = result['sql_info'].copy()
        sql_info['request'] = result.get('request', {})
        sql_queries.append(sql_info)

    return self.execute_batch(sql_queries, **execute_params)

