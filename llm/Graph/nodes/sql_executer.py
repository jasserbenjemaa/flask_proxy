import os
import re
import json
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from supabase import create_client
from urllib.parse import urlparse, parse_qs

load_dotenv()


def determine_http_method(client_request: Dict[str, Any]) -> str:
  """Determine HTTP method from client request"""
  if 'method' in client_request:
    return client_request['method'].upper()

  # Infer from request data
  if client_request.get('data') or client_request.get('body'):
    return 'POST' if not client_request.get('resource_id') else 'PUT'
  elif client_request.get('delete', False):
    return 'DELETE'
  else:
    return 'GET'


def parse_url_and_extract_params(url: str) -> Dict[str, Any]:
  """Parse URL to extract ID, query parameters, and route pattern"""

  # Handle URLs without scheme (like localhost:5100/users/123)
  if not url.startswith(('http://', 'https://')):
    url = 'http://' + url

  parsed = urlparse(url)

  # Debug: Print parsed components
  print(f"DEBUG - Parsed URL components:")
  print(f"  scheme: {parsed.scheme}")
  print(f"  netloc: {parsed.netloc}")
  print(f"  path: {parsed.path}")
  print(f"  query: {parsed.query}")

  # Extract path parts (exclude empty strings)
  path_parts = [part for part in parsed.path.strip('/').split('/') if part]
  print(f"  path_parts: {path_parts}")

  query_params = parse_qs(parsed.query)

  # Extract ID if present (assuming it's numeric or UUID-like)
  resource_id = None
  route_pattern = []

  for part in path_parts:
    # Check if it's a numeric ID
    if re.match(r'^\d+$', part):
      resource_id = part
      route_pattern.append('<id>')
      print(f"  Found numeric ID: {part}")
    # Check if it's a UUID (more strict pattern)
    elif re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', part, re.IGNORECASE):
      resource_id = part
      route_pattern.append('<id>')
      print(f"  Found UUID: {part}")
    # Check if it's a malformed UUID (like yours: 123e4567-e89b-3-a456-426614174000)
    elif re.match(r'^[a-f0-9-]{20,40}$', part, re.IGNORECASE) and '-' in part:
      resource_id = part
      route_pattern.append('<id>')
      print(f"  Found UUID-like ID: {part}")
    else:
      route_pattern.append(part)
      print(f"  Found route part: {part}")

  result = {
    "resource_id": resource_id,
    "route_pattern": '/' + '/'.join(route_pattern) if route_pattern else '/',
    "query_params": {k: v[0] if len(v) == 1 else v for k, v in query_params.items()},
    "path_parts": path_parts
  }

  print(f"  Final result: {result}")
  return result


class SQLQueryIntegrator:
  def __init__(self):
    # Initialize Gemini LLM
    self.llm = ChatGoogleGenerativeAI(
      model="gemini-2.0-flash-exp",
      google_api_key=os.getenv("GEMINI_API_KEY"),
      temperature=0.1
    )

    # Initialize Supabase
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
      self.supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
      )
    else:
      self.supabase = None

  def build_dynamic_sql(self,
                        extracted_queries: List[Dict[str, Any]],
                        url: str,
                        client_request: Dict[str, Any],
                        table_name: str) -> Dict[str, Any]:
    """Build dynamic SQL query based on URL, request, and extracted patterns"""

    url_info = parse_url_and_extract_params(url)
    http_method = determine_http_method(client_request)

    prompt = f"""
        Based on the following information, generate the appropriate SQL query:

        URL: {url}
        HTTP Method: {http_method}
        Resource ID: {url_info.get('resource_id')}
        Query Parameters: {url_info.get('query_params')}
        Table Name: {table_name}
        Client Request Data: {json.dumps(client_request, indent=2)}

        Extracted SQL Patterns from Flask Code:
        {json.dumps(extracted_queries, indent=2)}

        Generate a specific SQL query that matches the request. Consider:
        - If there's an ID in URL, use it in WHERE clause
        - If it's POST/PUT with data, use the data for INSERT/UPDATE
        - If there are query parameters (limit, offset, filters), include them
        - Match the operation type with HTTP method (GET=SELECT, POST=INSERT, PUT=UPDATE, DELETE=DELETE)

        Return ONLY a JSON object with this structure:
        {{
            "sql": "SELECT * FROM users WHERE id = 123;",
            "operation": "SELECT",
            "parameters": {{"id": "123", "limit": 10}},
            "explanation": "Brief explanation of the generated query"
        }}
        """

    try:
      response = self.llm.invoke(prompt)
      content = response.content.strip()

      # Clean response
      if content.startswith('```json'):
        content = content[7:-3]
      elif content.startswith('```'):
        content = content[3:-3]

      result = json.loads(content)

      # Add URL info to result
      result.update({
        "url_info": url_info,
        "http_method": http_method,
        "table_name": table_name
      })

      return result

    except Exception as e:
      print(f"Error building dynamic SQL: {e}")
      return self._fallback_sql_builder(url_info, http_method, client_request, table_name)

  def _fallback_sql_builder(self, url_info: Dict[str, Any], http_method: str,
                            client_request: Dict[str, Any], table_name: str) -> Dict[str, Any]:
    """Fallback SQL builder when LLM fails"""
    resource_id = url_info.get('resource_id')
    query_params = url_info.get('query_params', {})

    if http_method == 'GET':
      if resource_id:
        sql = f"SELECT * FROM {table_name} WHERE id = '{resource_id}';"
      else:
        sql = f"SELECT * FROM {table_name}"
        if 'limit' in query_params:
          sql += f" LIMIT {query_params['limit']}"
        sql += ";"

    elif http_method == 'POST':
      data = client_request.get('data', {})
      if data:
        columns = ', '.join(data.keys())
        values = ', '.join([f"'{v}'" for v in data.values()])
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({values});"
      else:
        sql = f"INSERT INTO {table_name} (name, email) VALUES ('default', 'default@example.com');"

    elif http_method == 'PUT':
      data = client_request.get('data', {})
      if data and resource_id:
        updates = ', '.join([f"{k} = '{v}'" for k, v in data.items()])
        sql = f"UPDATE {table_name} SET {updates} WHERE id = '{resource_id}';"
      else:
        sql = f"UPDATE {table_name} SET updated_at = NOW() WHERE id = '{resource_id}';"

    elif http_method == 'DELETE':
      if resource_id:
        sql = f"DELETE FROM {table_name} WHERE id = '{resource_id}';"
      else:
        sql = f"DELETE FROM {table_name} WHERE id IS NULL;"  # Safe fallback

    else:
      sql = f"SELECT * FROM {table_name};"

    return {
      "sql": sql,
      "operation": http_method,
      "parameters": {"id": resource_id, **query_params},
      "explanation": f"Fallback {http_method} operation on {table_name}",
      "url_info": url_info,
      "http_method": http_method,
      "table_name": table_name
    }

  def execute_dynamic_sql(self, sql_info: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the dynamically built SQL query"""
    if not self.supabase:
      return {"success": False, "error": "Supabase not configured"}

    try:
      sql = sql_info['sql']
      table_name = sql_info['table_name']
      operation = sql_info['operation']
      resource_id = sql_info.get('url_info', {}).get('resource_id')

      if operation == 'GET' or sql.upper().startswith('SELECT'):
        query = self.supabase.table(table_name).select('*')

        if resource_id:
          query = query.eq('id', resource_id)

        # Add query parameters
        query_params = sql_info.get('parameters', {})
        if 'limit' in query_params:
          query = query.limit(int(query_params['limit']))
        if 'offset' in query_params:
          query = query.offset(int(query_params['offset']))

        result = query.execute()

      elif operation == 'POST' or sql.upper().startswith('INSERT'):
        # Extract data from SQL or use parameters
        data = self._extract_insert_data(sql)
        result = self.supabase.table(table_name).insert(data).execute()

      elif operation == 'PUT' or sql.upper().startswith('UPDATE'):
        # Extract update data from SQL
        data = self._extract_update_data(sql)
        query = self.supabase.table(table_name).update(data)
        if resource_id:
          query = query.eq('id', resource_id)
        result = query.execute()

      elif operation == 'DELETE' or sql.upper().startswith('DELETE'):
        query = self.supabase.table(table_name).delete()
        if resource_id:
          query = query.eq('id', resource_id)
        result = query.execute()

      else:
        return {"success": False, "error": f"Unsupported operation: {operation}"}

      return {
        "success": True,
        "data": result.data,
        "count": len(result.data) if result.data else 0,
        "sql_executed": sql,
        "operation": operation
      }

    except Exception as e:
      return {"success": False, "error": str(e), "sql": sql_info.get('sql')}

  def _extract_insert_data(self, sql: str) -> Dict[str, Any]:
    """Extract data from INSERT SQL statement"""
    # Simple regex to extract INSERT data
    match = re.search(r'INSERT INTO \w+ \(([^)]+)\) VALUES \(([^)]+)\)', sql, re.IGNORECASE)
    if match:
      columns = [col.strip().strip("'\"") for col in match.group(1).split(',')]
      values = [val.strip().strip("'\"") for val in match.group(2).split(',')]
      return dict(zip(columns, values))

    # Fallback
    return {"name": "dynamic_user", "email": "dynamic@example.com"}

  def _extract_update_data(self, sql: str) -> Dict[str, Any]:
    """Extract data from UPDATE SQL statement"""
    # Simple regex to extract UPDATE data
    match = re.search(r'SET (.+?) WHERE', sql, re.IGNORECASE)
    if match:
      updates = {}
      for update in match.group(1).split(','):
        if '=' in update:
          key, value = update.split('=', 1)
          updates[key.strip()] = value.strip().strip("'\"")
      return updates

    # Fallback
    return {"updated_at": "NOW()"}

  def process_request(self,
                      url: str,
                      client_request: Dict[str, Any],
                      table_name: str,
                      extracted_queries: List[Dict[str, Any]],
                      execute: bool = False) -> Dict[str, Any]:
    """Main function to process URL request and integrate with SQL"""

    print(f"🔗 Processing URL: {url}")
    print(f"📋 Request: {client_request}")
    print(f"🗄️  Table: {table_name}")

    # Build dynamic SQL
    sql_info = self.build_dynamic_sql(extracted_queries, url, client_request, table_name)
    print(f"🔍 Generated SQL: {sql_info['sql']}")
    print(f"💡 Explanation: {sql_info['explanation']}")

    result = {
      "url": url,
      "request": client_request,
      "table_name": table_name,
      "sql_info": sql_info,
      "execution_result": None
    }

    if execute:
      print("🚀 Executing query...")
      execution_result = self.execute_dynamic_sql(sql_info)
      result["execution_result"] = execution_result

      status = "✅" if execution_result['success'] else "❌"
      print(f"   {status} Result: {execution_result.get('error', f'{execution_result.get('count', 0)} rows affected')}")

    return result


# Example usage function
def main():
  from Graph.nodes.sql_extractor import SimpleFlaskSQLExtractor  # Import your previous extractor

  # Initialize both classes
  extractor = SimpleFlaskSQLExtractor()
  integrator = SQLQueryIntegrator()

  # Sample Flask code for context
  flask_code = """
    @app.route('/users', methods=['GET'])
    def get_users():
        response = supabase.table('users').select("*").execute()
        return jsonify(response.data)

    @app.route('/users/<user_id>', methods=['GET'])
    def get_user(user_id):
        response = supabase.table('users').select("*").eq('id', user_id).execute()
        return jsonify(response.data)

    @app.route('/users', methods=['POST'])
    def create_user():
        data = request.json
        response = supabase.table('users').insert(data).execute()
        return jsonify(response.data)
    """

  # Extract SQL patterns
  extracted_queries = extractor.extract_sql(flask_code)

  # Test different scenarios
  test_cases = [
    {
      "url": "https://api.example.com/users",
      "request": {"method": "GET", "query_params": {"limit": 10}},
      "table": "users"
    },
    {
      "url": "https://api.example.com/users/123",
      "request": {"method": "GET"},
      "table": "users"
    },
    {
      "url": "https://api.example.com/users",
      "request": {
        "method": "POST",
        "data": {"name": "John Doe", "email": "john@example.com", "age": 30}
      },
      "table": "users"
    },
    {
      "url": "https://api.example.com/users/456",
      "request": {
        "method": "PUT",
        "data": {"name": "Jane Smith", "email": "jane@example.com"}
      },
      "table": "users"
    },
    {
      "url": "https://api.example.com/users/789",
      "request": {"method": "DELETE"},
      "table": "users"
    }
  ]

  print("🧪 Testing SQL Query Integration:")
  print("=" * 50)

  for i, test_case in enumerate(test_cases, 1):
    print(f"\n🔸 Test Case {i}:")
    result = integrator.process_request(
      url=test_case["url"],
      client_request=test_case["request"],
      table_name=test_case["table"],
      extracted_queries=extracted_queries,
      execute=False  # Set to True to actually execute
    )

    print(f"   📊 Operation: {result['sql_info']['operation']}")
    print(f"   🔧 Parameters: {result['sql_info']['parameters']}")
    print("-" * 30)


if __name__ == "__main__":
  main()