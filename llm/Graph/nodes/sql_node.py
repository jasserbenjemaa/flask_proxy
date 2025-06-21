import json
import time
import traceback
import sys
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dotenv import load_dotenv
import logging

# Import all the classes (assuming they're in the same directory or properly installed)
try:
  from Graph.nodes.sql_extractor import SimpleFlaskSQLExtractor
  from Graph.nodes.sql_executer import SQLQueryIntegrator
  from Graph.nodes.sql_main import SQLBatchExecutor, QueryResult
except ImportError as e:
  print(f"❌ Import Error: {e}")
  print("Please ensure all required modules are in the correct path")
  sys.exit(1)

load_dotenv()


class ErrorDetails:
  """Class to capture detailed error information"""

  def __init__(self, error: Exception, context: str = "", step: str = ""):
    self.error = error
    self.error_type = type(error).__name__
    self.error_message = str(error)
    self.context = context
    self.step = step
    self.timestamp = datetime.now().isoformat()
    self.traceback = traceback.format_exc()

  def to_dict(self) -> Dict[str, Any]:
    return {
      "error_type": self.error_type,
      "error_message": self.error_message,
      "context": self.context,
      "step": self.step,
      "timestamp": self.timestamp,
      "traceback": self.traceback
    }

  def print_error(self):
    """Print formatted error details"""
    print(f"❌ ERROR in {self.step}: {self.error_type}")
    print(f"   Message: {self.error_message}")
    if self.context:
      print(f"   Context: {self.context}")
    print(f"   Time: {self.timestamp}")
    print(f"   Full Traceback:")
    print(f"   {'-' * 50}")
    for line in self.traceback.split('\n'):
      if line.strip():
        print(f"   {line}")
    print(f"   {'-' * 50}")


class FlaskSQLProcessor:
  """
  Complete Flask-to-SQL processing pipeline that integrates all components
  with comprehensive error handling
  """

  def __init__(self, connection_config: Optional[Dict[str, str]] = None):
    """
    Initialize the complete Flask SQL processor

    Args:
        connection_config: Optional database connection configuration
    """
    # Initialize logging with more detailed format
    logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    self.logger = logging.getLogger(__name__)

    self.errors = []  # Store all errors encountered

    # Initialize components with error handling
    try:
      self.logger.info("Initializing SimpleFlaskSQLExtractor...")
      self.extractor = SimpleFlaskSQLExtractor()
      self.logger.info("✅ SimpleFlaskSQLExtractor initialized successfully")
    except Exception as e:
      error_detail = ErrorDetails(e, "Failed to initialize SimpleFlaskSQLExtractor", "Initialization")
      self.errors.append(error_detail)
      error_detail.print_error()
      self.extractor = None

    try:
      self.logger.info("Initializing SQLQueryIntegrator...")
      self.integrator = SQLQueryIntegrator()
      self.logger.info("✅ SQLQueryIntegrator initialized successfully")
    except Exception as e:
      error_detail = ErrorDetails(e, "Failed to initialize SQLQueryIntegrator", "Initialization")
      self.errors.append(error_detail)
      error_detail.print_error()
      self.integrator = None

    try:
      self.logger.info("Initializing SQLBatchExecutor...")
      self.executor = SQLBatchExecutor(connection_config)
      self.logger.info("✅ SQLBatchExecutor initialized successfully")
    except Exception as e:
      error_detail = ErrorDetails(e, "Failed to initialize SQLBatchExecutor", "Initialization")
      self.errors.append(error_detail)
      error_detail.print_error()
      self.executor = None

    if self.errors:
      print(f"⚠️  Warning: {len(self.errors)} errors occurred during initialization")
    else:
      self.logger.info("🎉 FlaskSQLProcessor initialized successfully")

  def process_flask_request(self,
                            flask_code: str,
                            url: str,
                            client_request: Dict[str, Any],
                            table_name: str,
                            execute: bool = True,
                            execution_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Complete end-to-end processing of Flask code to SQL execution with comprehensive error handling
    """

    if execution_options is None:
      execution_options = {
        'continue_on_error': True,
        'max_retries': 1,
        'delay_between_queries': 0.1
      }

    start_time = time.time()
    step_errors = []

    self.logger.info(f"🚀 Starting Flask-to-SQL processing for URL: {url}")

    # Initialize result structure
    result = {
      'success': False,
      'processing_time': 0.0,
      'timestamp': datetime.now().isoformat(),
      'input': {
        'url': url,
        'client_request': client_request,
        'table_name': table_name,
        'flask_code_length': len(flask_code),
        'execute': execute
      },
      'step_1_extraction': None,
      'step_2_integration': None,
      'step_3_execution': None,
      'supabase_data': None,
      'errors': [],
      'summary': {}
    }

    # Step 1: Extract SQL patterns from Flask code
    extracted_queries = []
    try:
      if not self.extractor:
        raise RuntimeError("SimpleFlaskSQLExtractor not initialized")

      self.logger.info("📝 Step 1: Extracting SQL patterns from Flask code...")
      print("📝 Step 1: Extracting SQL patterns from Flask code...")

      extracted_queries = self.extractor.extract_sql(flask_code)

      if not extracted_queries:
        self.logger.warning("No SQL patterns found in Flask code")
        print("⚠️  Warning: No SQL patterns found in Flask code")
        extracted_queries = []

      self.logger.info(f"   ✅ Found {len(extracted_queries)} SQL patterns")
      print(f"   ✅ Found {len(extracted_queries)} SQL patterns")

      result['step_1_extraction'] = {
        'extracted_queries': extracted_queries,
        'patterns_found': len(extracted_queries),
        'success': True
      }

    except Exception as e:
      error_detail = ErrorDetails(
        e,
        f"Failed to extract SQL patterns from Flask code. Flask code length: {len(flask_code)}",
        "Step 1: SQL Extraction"
      )
      step_errors.append(error_detail)
      error_detail.print_error()

      result['step_1_extraction'] = {
        'extracted_queries': [],
        'patterns_found': 0,
        'success': False,
        'error': error_detail.to_dict()
      }

    # Step 2: Generate dynamic SQL based on URL and request
    sql_integration_result = None
    sql_info = {}
    try:
      if not self.integrator:
        raise RuntimeError("SQLQueryIntegrator not initialized")

      self.logger.info("🔍 Step 2: Generating dynamic SQL query...")
      print("🔍 Step 2: Generating dynamic SQL query...")

      sql_integration_result = self.integrator.process_request(
        url=url,
        client_request=client_request,
        table_name=table_name,
        extracted_queries=extracted_queries,
        execute=False  # We'll execute later with our batch executor
      )

      sql_info = sql_integration_result.get('sql_info', {})

      if not sql_info or not sql_info.get('sql'):
        raise ValueError(f"No SQL generated from integration. Result: {sql_integration_result}")

      self.logger.info(f"   ✅ Generated SQL: {sql_info.get('sql', 'N/A')}")
      self.logger.info(f"   ✅ Operation: {sql_info.get('operation', 'N/A')}")
      print(f"   ✅ Generated SQL: {sql_info.get('sql', 'N/A')}")
      print(f"   ✅ Operation: {sql_info.get('operation', 'N/A')}")

      result['step_2_integration'] = {
        'sql_info': sql_info,
        'integration_result': sql_integration_result,
        'success': True
      }

    except Exception as e:
      error_detail = ErrorDetails(
        e,
        f"Failed to generate dynamic SQL. URL: {url}, Request: {client_request}",
        "Step 2: SQL Integration"
      )
      step_errors.append(error_detail)
      error_detail.print_error()

      result['step_2_integration'] = {
        'sql_info': {},
        'integration_result': None,
        'success': False,
        'error': error_detail.to_dict()
      }

    # Step 3: Execute SQL if requested
    execution_result = None
    supabase_data = None
    if execute and sql_info:
      try:
        if not self.executor:
          raise RuntimeError("SQLBatchExecutor not initialized")

        self.logger.info("🚀 Step 3: Executing SQL query...")
        print("🚀 Step 3: Executing SQL query...")

        # Prepare SQL for batch execution
        sql_queries = [sql_info]

        # Execute with batch executor
        execution_result = self.executor.execute_batch(
          sql_queries=sql_queries,
          **execution_options
        )

        success_count = execution_result['summary']['successful_queries']
        failed_count = execution_result['summary']['failed_queries']

        if success_count > 0:
          self.logger.info(f"   ✅ SQL executed successfully: {success_count} queries")
          print(f"   ✅ SQL executed successfully: {success_count} queries")

          # Extract the actual Supabase data from the first successful result
          if execution_result['results']:
            first_result = execution_result['results'][0]
            if first_result['success']:
              supabase_data = first_result['data']
              data_count = len(supabase_data) if isinstance(supabase_data, list) else (1 if supabase_data else 0)
              self.logger.info(f"   📊 Retrieved {data_count} records")
              print(f"   📊 Retrieved {data_count} records")

        if failed_count > 0:
          error_msg = f"SQL execution failed: {failed_count} queries"
          self.logger.error(f"   ❌ {error_msg}")
          print(f"   ❌ {error_msg}")

          # Log individual execution errors
          for i, exec_result in enumerate(execution_result.get('results', [])):
            if not exec_result.get('success'):
              exec_error = ErrorDetails(
                Exception(exec_result.get('error', 'Unknown execution error')),
                f"Query {i + 1} execution failed. SQL: {exec_result.get('sql', 'N/A')}",
                "Step 3: SQL Execution - Individual Query"
              )
              step_errors.append(exec_error)
              exec_error.print_error()

        result['step_3_execution'] = {
          'execution_result': execution_result,
          'success': success_count > 0
        }

      except Exception as e:
        error_detail = ErrorDetails(
          e,
          f"Failed to execute SQL. SQL Info: {sql_info}",
          "Step 3: SQL Execution"
        )
        step_errors.append(error_detail)
        error_detail.print_error()

        result['step_3_execution'] = {
          'execution_result': None,
          'success': False,
          'error': error_detail.to_dict()
        }

    elif execute and not sql_info:
      warning_msg = "Cannot execute SQL - no SQL generated in Step 2"
      self.logger.warning(f"⚠️  {warning_msg}")
      print(f"⚠️  {warning_msg}")

      result['step_3_execution'] = {
        'execution_result': None,
        'success': False,
        'skipped_reason': warning_msg
      }

    # Finalize result
    total_time = time.time() - start_time

    # Determine overall success
    overall_success = (
        result.get('step_1_extraction', {}).get('success', False) and
        result.get('step_2_integration', {}).get('success', False) and
        (not execute or result.get('step_3_execution', {}).get('success', False))
    )

    result.update({
      'success': overall_success,
      'processing_time': total_time,
      'supabase_data': supabase_data,
      'errors': [error.to_dict() for error in step_errors],
      'error_count': len(step_errors),
      'summary': {
        'sql_generated': sql_info.get('sql', 'N/A'),
        'operation_type': sql_info.get('operation', 'N/A'),
        'executed': execute,
        'execution_success': execution_result['success'] if execution_result else None,
        'rows_affected': self._get_total_rows_affected(execution_result) if execution_result else 0,
        'data_count': len(supabase_data) if isinstance(supabase_data, list) else (1 if supabase_data else 0),
        'total_errors': len(step_errors)
      }
    })

    # Print final status
    if overall_success:
      self.logger.info(f"🎉 Processing completed successfully in {total_time:.2f}s")
      print(f"🎉 Processing completed successfully in {total_time:.2f}s")
    else:
      self.logger.error(f"❌ Processing completed with errors in {total_time:.2f}s")
      print(f"❌ Processing completed with {len(step_errors)} errors in {total_time:.2f}s")

    # Print error summary
    if step_errors:
      print(f"\n📋 ERROR SUMMARY:")
      print(f"   Total Errors: {len(step_errors)}")
      for i, error in enumerate(step_errors, 1):
        print(f"   {i}. {error.step}: {error.error_type} - {error.error_message}")

    return result

  def _get_total_rows_affected(self, execution_result: Dict[str, Any]) -> int:
    """Extract total rows affected from execution result"""
    if not execution_result or 'results' not in execution_result:
      return 0

    total_rows = 0
    for result in execution_result['results']:
      total_rows += result.get('rows_affected', 0)

    return total_rows

  def get_supabase_data(self, processing_result: Dict[str, Any]) -> Any:
    """
    Helper method to extract Supabase data from processing result

    Args:
        processing_result: Result from process_flask_request()

    Returns:
        The actual Supabase data or None if not available
    """
    try:
      # Direct access to supabase_data
      if 'supabase_data' in processing_result:
        return processing_result['supabase_data']

      # Fallback: extract from execution results
      if (processing_result.get('step_3_execution') and
          processing_result['step_3_execution'].get('execution_result') and
          processing_result['step_3_execution']['execution_result'].get('results')):

        first_result = processing_result['step_3_execution']['execution_result']['results'][0]
        if first_result.get('success'):
          return first_result.get('data')

      return None

    except Exception as e:
      error_detail = ErrorDetails(e, "Failed to extract Supabase data from result", "Data Extraction Helper")
      error_detail.print_error()
      return None

  def execute_and_get_data(self,
                           flask_code: str,
                           url: str,
                           client_request: Dict[str, Any],
                           table_name: str,
                           execution_options: Optional[Dict[str, Any]] = None) -> tuple[bool, Any, str]:
    """
    Convenient method to execute SQL and get just the data with error handling

    Returns:
        tuple: (success, data, error_message)
    """
    try:
      result = self.process_flask_request(
        flask_code=flask_code,
        url=url,
        client_request=client_request,
        table_name=table_name,
        execute=True,
        execution_options=execution_options
      )

      if result['success']:
        data = self.get_supabase_data(result)
        return True, data, ""
      else:
        # Compile error messages
        error_messages = []
        for error in result.get('errors', []):
          error_messages.append(f"{error.get('step', 'Unknown')}: {error.get('error_message', 'Unknown error')}")

        combined_error = " | ".join(error_messages) if error_messages else result.get('error', 'Unknown error')
        return False, None, combined_error

    except Exception as e:
      error_detail = ErrorDetails(e, "Failed in execute_and_get_data method", "Execute and Get Data")
      error_detail.print_error()
      return False, None, str(e)

  def print_all_errors(self):
    """Print all errors encountered during processing"""
    if not self.errors:
      print("✅ No errors recorded")
      return

    print(f"\n🚨 ALL ERRORS ENCOUNTERED ({len(self.errors)} total):")
    print("=" * 60)

    for i, error in enumerate(self.errors, 1):
      print(f"\nError #{i}:")
      error.print_error()

  def get_error_summary(self) -> Dict[str, Any]:
    """Get a summary of all errors"""
    return {
      'total_errors': len(self.errors),
      'error_types': list(set(error.error_type for error in self.errors)),
      'steps_with_errors': list(set(error.step for error in self.errors if error.step)),
      'errors': [error.to_dict() for error in self.errors]
    }


def process_flask_to_sql(flask_code: str,
                         url: str,
                         client_request: Dict[str, Any],
                         table_name: str,
                         execute: bool = True,
                         connection_config: Optional[Dict[str, str]] = None,
                         execution_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
  """
  Convenient function to process Flask code to SQL execution in one call with error handling

  Args:
      flask_code: The Flask application code to analyze
      url: The API endpoint URL being called
      client_request: The client request data (method, data, params, etc.)
      table_name: The database table name to operate on
      execute: Whether to actually execute the SQL queries (default: True)
      connection_config: Optional database connection configuration
      execution_options: Optional execution parameters

  Returns:
      Dictionary containing all processing results and execution outcomes
  """

  try:
    processor = FlaskSQLProcessor(connection_config)
    return processor.process_flask_request(
      flask_code=flask_code,
      url=url,
      client_request=client_request,
      table_name=table_name,
      execute=execute,
      execution_options=execution_options
    )
  except Exception as e:
    error_detail = ErrorDetails(e, "Failed in process_flask_to_sql function", "Main Function")
    error_detail.print_error()

    return {
      'success': False,
      'error': str(e),
      'errors': [error_detail.to_dict()],
      'timestamp': datetime.now().isoformat()
    }


def get_supabase_data_simple(flask_code: str,
                             url: str,
                             client_request: Dict[str, Any],
                             table_name: str) -> tuple[bool, Any, str]:
  """
  Simple function to just get the Supabase data with error handling

  Returns:
      tuple: (success, data, error_message)
  """
  try:
    processor = FlaskSQLProcessor()
    return processor.execute_and_get_data(flask_code, url, client_request, table_name)
  except Exception as e:
    error_detail = ErrorDetails(e, "Failed in get_supabase_data_simple function", "Simple Data Function")
    error_detail.print_error()
    return False, None, str(e)


# Enhanced sql_node function with comprehensive error handling
def sql_node(sample_flask_code: str, client_request: Dict[str, Any], url: str, table_name: str) -> Dict[str, Any]:
  """
  Enhanced SQL node function with comprehensive error handling and reporting

  Args:
      sample_flask_code: Flask application code to analyze
      client_request: Client request data
      url: API endpoint URL
      table_name: Database table name

  Returns:
      Dictionary containing processing results and error details
  """

  print("🧪 Enhanced Flask-to-SQL Integration with Comprehensive Error Handling")
  print("=" * 80)

  start_time = time.time()

  try:
    # Initialize processor
    print("🔧 Initializing FlaskSQLProcessor...")
    processor = FlaskSQLProcessor()

    # Print initialization errors if any
    if processor.errors:
      print(f"⚠️  Initialization completed with {len(processor.errors)} errors")
      processor.print_all_errors()
    else:
      print("✅ Initialization successful")

    # Process the request
    print(f"\n📋 Processing Request:")
    print(f"   URL: {url}")
    print(f"   Method: {client_request.get('method', 'Unknown')}")
    print(f"   Table: {table_name}")
    print(f"   Flask Code Length: {len(sample_flask_code)} characters")

    result = processor.process_flask_request(
      flask_code=sample_flask_code,
      url=url,
      client_request=client_request,
      table_name=table_name,
      execute=True
    )

    # Print results summary
    print(f"\n📊 PROCESSING RESULTS:")
    print(f"   Overall Success: {'✅' if result['success'] else '❌'}")
    print(f"   Processing Time: {result['processing_time']:.2f}s")
    print(f"   Total Errors: {result.get('error_count', 0)}")

    if result['success']:
      print(f"   SQL Generated: {result['summary']['sql_generated']}")
      print(f"   Operation: {result['summary']['operation_type']}")
      print(f"   Data Count: {result['summary']['data_count']}")

      # Show Supabase data if available
      supabase_data = result.get('supabase_data')
      if supabase_data:
        print(f"   📊 Supabase Data Retrieved:")
        if isinstance(supabase_data, list):
          print(f"      - Type: List with {len(supabase_data)} items")
          if supabase_data and len(supabase_data) > 0:
            print(f"      - First item: {supabase_data[0]}")
        else:
          print(f"      - Type: {type(supabase_data).__name__}")
          print(f"      - Data: {supabase_data}")

    # Print detailed step results
    print(f"\n🔍 STEP-BY-STEP RESULTS:")

    # Step 1
    step1 = result.get('step_1_extraction', {})
    step1_status = "✅" if step1.get('success') else "❌"
    print(f"   Step 1 (SQL Extraction): {step1_status}")
    if step1.get('success'):
      print(f"      - Patterns found: {step1.get('patterns_found', 0)}")
    else:
      print(f"      - Error: {step1.get('error', {}).get('error_message', 'Unknown')}")

    # Step 2
    step2 = result.get('step_2_integration', {})
    step2_status = "✅" if step2.get('success') else "❌"
    print(f"   Step 2 (SQL Integration): {step2_status}")
    if step2.get('success'):
      sql_info = step2.get('sql_info', {})
      print(f"      - SQL: {sql_info.get('sql', 'N/A')}")
      print(f"      - Operation: {sql_info.get('operation', 'N/A')}")
    else:
      print(f"      - Error: {step2.get('error', {}).get('error_message', 'Unknown')}")

    # Step 3
    step3 = result.get('step_3_execution', {})
    if step3:
      step3_status = "✅" if step3.get('success') else "❌"
      print(f"   Step 3 (SQL Execution): {step3_status}")
      if step3.get('success'):
        exec_result = step3.get('execution_result', {})
        summary = exec_result.get('summary', {})
        print(f"      - Successful queries: {summary.get('successful_queries', 0)}")
        print(f"      - Failed queries: {summary.get('failed_queries', 0)}")
      else:
        print(f"      - Error: {step3.get('error', {}).get('error_message', 'Unknown')}")
    else:
      print(f"   Step 3 (SQL Execution): ⏭️  Skipped")

    # Print all errors in detail
    if result.get('errors'):
      print(f"\n🚨 DETAILED ERROR REPORT:")
      for i, error in enumerate(result['errors'], 1):
        print(f"   Error #{i}:")
        print(f"      Step: {error.get('step', 'Unknown')}")
        print(f"      Type: {error.get('error_type', 'Unknown')}")
        print(f"      Message: {error.get('error_message', 'Unknown')}")
        print(f"      Context: {error.get('context', 'No context')}")
        print(f"      Time: {error.get('timestamp', 'Unknown')}")

    total_time = time.time() - start_time
    print(f"\n⏱️  Total Execution Time: {total_time:.2f}s")

    return result

  except Exception as e:
    total_time = time.time() - start_time
    error_detail = ErrorDetails(e, "Critical failure in sql_node function", "SQL Node Main")
    error_detail.print_error()

    print(f"\n💥 CRITICAL ERROR in SQL Node:")
    print(f"   Total Time: {total_time:.2f}s")

    return {
      'success': False,
      'error': str(e),
      'errors': [error_detail.to_dict()],
      'processing_time': total_time,
      'timestamp': datetime.now().isoformat(),
      'critical_failure': True
    }

  # Add this function to your sql_node.py file or modify the existing sql_node function


def sql_node_with_data_return(sample_flask_code: str, client_request: Dict[str, Any], url: str, table_name: str) -> \
Dict[str, Any]:
  """
  Enhanced SQL node function that ensures data is properly returned for the formatter

  Args:
      sample_flask_code: Flask application code to analyze
      client_request: Client request data
      url: API endpoint URL
      table_name: Database table name

  Returns:
      Dictionary containing processing results, error details, and properly formatted data
  """

  print("🧪 Enhanced Flask-to-SQL Integration with Data Return")
  print("=" * 80)

  start_time = time.time()

  try:
    # Initialize processor
    print("🔧 Initializing FlaskSQLProcessor...")
    processor = FlaskSQLProcessor()

    # Print initialization errors if any
    if processor.errors:
      print(f"⚠️  Initialization completed with {len(processor.errors)} errors")
      processor.print_all_errors()
    else:
      print("✅ Initialization successful")

    # Process the request
    print(f"\n📋 Processing Request:")
    print(f"   URL: {url}")
    print(f"   Method: {client_request.get('method', 'Unknown')}")
    print(f"   Table: {table_name}")
    print(f"   Flask Code Length: {len(sample_flask_code)} characters")

    result = processor.process_flask_request(
      flask_code=sample_flask_code,
      url=url,
      client_request=client_request,
      table_name=table_name,
      execute=True
    )

    # Ensure supabase_data is properly set
    if result['success'] and not result.get('supabase_data'):
      # Try to extract data from execution results
      if (result.get('step_3_execution') and
          result['step_3_execution'].get('execution_result') and
          result['step_3_execution']['execution_result'].get('results')):

        exec_results = result['step_3_execution']['execution_result']['results']
        for exec_result in exec_results:
          if exec_result.get('success') and exec_result.get('data'):
            result['supabase_data'] = exec_result['data']
            break

    # Print results summary
    print(f"\n📊 PROCESSING RESULTS:")
    print(f"   Overall Success: {'✅' if result['success'] else '❌'}")
    print(f"   Processing Time: {result['processing_time']:.2f}s")
    print(f"   Total Errors: {result.get('error_count', 0)}")

    if result['success']:
      print(f"   SQL Generated: {result['summary']['sql_generated']}")
      print(f"   Operation: {result['summary']['operation_type']}")
      print(f"   Data Count: {result['summary']['data_count']}")

      # Show Supabase data if available
      supabase_data = result.get('supabase_data')
      if supabase_data:
        print(f"   📊 Supabase Data Retrieved:")
        if isinstance(supabase_data, list):
          print(f"      - Type: List with {len(supabase_data)} items")
          if supabase_data and len(supabase_data) > 0:
            print(f"      - First item: {json.dumps(supabase_data[0], indent=6, default=str)}")
        else:
          print(f"      - Type: {type(supabase_data).__name__}")
          print(f"      - Data: {json.dumps(supabase_data, indent=6, default=str)}")
      else:
        print(f"   ⚠️  No Supabase data returned")

    # Print detailed step results
    print(f"\n🔍 STEP-BY-STEP RESULTS:")

    # Step 1
    step1 = result.get('step_1_extraction', {})
    step1_status = "✅" if step1.get('success') else "❌"
    print(f"   Step 1 (SQL Extraction): {step1_status}")
    if step1.get('success'):
      print(f"      - Patterns found: {step1.get('patterns_found', 0)}")
    else:
      print(f"      - Error: {step1.get('error', {}).get('error_message', 'Unknown')}")

    # Step 2
    step2 = result.get('step_2_integration', {})
    step2_status = "✅" if step2.get('success') else "❌"
    print(f"   Step 2 (SQL Integration): {step2_status}")
    if step2.get('success'):
      sql_info = step2.get('sql_info', {})
      print(f"      - SQL: {sql_info.get('sql', 'N/A')}")
      print(f"      - Operation: {sql_info.get('operation', 'N/A')}")
    else:
      print(f"      - Error: {step2.get('error', {}).get('error_message', 'Unknown')}")

    # Step 3
    step3 = result.get('step_3_execution', {})
    if step3:
      step3_status = "✅" if step3.get('success') else "❌"
      print(f"   Step 3 (SQL Execution): {step3_status}")
      if step3.get('success'):
        exec_result = step3.get('execution_result', {})
        summary = exec_result.get('summary', {})
        print(f"      - Successful queries: {summary.get('successful_queries', 0)}")
        print(f"      - Failed queries: {summary.get('failed_queries', 0)}")

        # Show execution results details
        if exec_result.get('results'):
          for i, res in enumerate(exec_result['results']):
            if res.get('success'):
              data = res.get('data')
              if data:
                data_info = f"List[{len(data)}]" if isinstance(data, list) else type(data).__name__
                print(f"      - Result {i + 1}: Success, Data: {data_info}")
              else:
                print(f"      - Result {i + 1}: Success, No data")
            else:
              print(f"      - Result {i + 1}: Failed - {res.get('error', 'Unknown error')}")
      else:
        print(f"      - Error: {step3.get('error', {}).get('error_message', 'Unknown')}")
    else:
      print(f"   Step 3 (SQL Execution): ⏭️  Skipped")

    # Print all errors in detail
    if result.get('errors'):
      print(f"\n🚨 DETAILED ERROR REPORT:")
      for i, error in enumerate(result['errors'], 1):
        print(f"   Error #{i}:")
        print(f"      Step: {error.get('step', 'Unknown')}")
        print(f"      Type: {error.get('error_type', 'Unknown')}")
        print(f"      Message: {error.get('error_message', 'Unknown')}")
        print(f"      Context: {error.get('context', 'No context')}")
        print(f"      Time: {error.get('timestamp', 'Unknown')}")

    total_time = time.time() - start_time
    print(f"\n⏱️  Total Execution Time: {total_time:.2f}s")

    # Ensure the result has the data properly structured for the formatter
    if result['success'] and result.get('supabase_data'):
      print(f"\n✅ Data ready for formatter: {type(result['supabase_data']).__name__}")
    elif result['success']:
      print(f"\n⚠️  Success but no data available for formatter")
    else:
      print(f"\n❌ Failed - no data available for formatter")

    return result

  except Exception as e:
    total_time = time.time() - start_time
    error_detail = ErrorDetails(e, "Critical failure in sql_node_with_data_return function", "SQL Node Main Enhanced")
    error_detail.print_error()

    print(f"\n💥 CRITICAL ERROR in SQL Node:")
    print(f"   Total Time: {total_time:.2f}s")

    return {
      'success': False,
      'error': str(e),
      'errors': [error_detail.to_dict()],
      'processing_time': total_time,
      'timestamp': datetime.now().isoformat(),
      'critical_failure': True,
      'supabase_data': None
    }

  # Alternative: Modify the original sql_node function to ensure data return
  # Add this at the end of the original sql_node function before returning result:


def ensure_data_in_result(result: Dict[str, Any]) -> Dict[str, Any]:
  """
  Ensure that the result contains properly formatted supabase_data
  """
  if result.get('success') and not result.get('supabase_data'):
    # Try to extract data from execution results
    if (result.get('step_3_execution') and
        result['step_3_execution'].get('execution_result') and
        result['step_3_execution']['execution_result'].get('results')):

      exec_results = result['step_3_execution']['execution_result']['results']
      for exec_result in exec_results:
        if exec_result.get('success') and exec_result.get('data'):
          result['supabase_data'] = exec_result['data']
          # Update summary data count
          if isinstance(exec_result['data'], list):
            result['summary']['data_count'] = len(exec_result['data'])
          elif exec_result['data']:
            result['summary']['data_count'] = 1
          break

  return result