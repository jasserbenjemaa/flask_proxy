import os
import re
import json
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


class SimpleFlaskSQLExtractor:
  def __init__(self):
    # Initialize Gemini LLM
    self.llm = ChatGoogleGenerativeAI(
      model="gemini-2.0-flash-exp",
      google_api_key=os.getenv("GEMINI_API_KEY"),
      temperature=0.1
    )

    # Initialize Supabase (optional)
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
      self.supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
      )
    else:
      self.supabase = None

  def extract_sql(self, flask_code: str) -> List[Dict[str, Any]]:
    """Extract SQL queries from Flask code"""
    prompt = f"""
        Extract SQL queries from this Flask code. Return only valid JSON array:

        [
          {{
            "sql": "SELECT * FROM users WHERE id = 1;",
            "type": "SELECT",
            "table": "users"
          }}
        ]

        Flask code:
        {flask_code}
        """

    try:
      response = self.llm.invoke(prompt)
      content = response.content.strip()

      # Clean response
      if content.startswith('```json'):
        content = content[7:-3]
      elif content.startswith('```'):
        content = content[3:-3]

      queries = json.loads(content)
      return queries if isinstance(queries, list) else []

    except Exception as e:
      print(f"Error extracting SQL: {e}")
      return self._manual_extract(flask_code)

  def _manual_extract(self, flask_code: str) -> List[Dict[str, Any]]:
    """Fallback manual extraction"""
    queries = []

    # Simple regex patterns
    patterns = [
      (r"\.select\([^)]*\)", "SELECT"),
      (r"\.insert\([^)]*\)", "INSERT"),
      (r"\.update\([^)]*\)", "UPDATE"),
      (r"\.delete\(\)", "DELETE")
    ]

    # Find table names
    table_matches = re.findall(r"\.table\(['\"](\w+)['\"]", flask_code)
    tables = list(set(table_matches))

    for pattern, op_type in patterns:
      if re.search(pattern, flask_code):
        table_name = tables[0] if tables else "unknown"
        sql = self._convert_to_sql(op_type, table_name)
        queries.append({
          "sql": sql,
          "type": op_type,
          "table": table_name
        })

    return queries[:2]  # Max 2 operations

  def _convert_to_sql(self, operation: str, table: str) -> str:
    """Convert operation to basic SQL"""
    if operation == "SELECT":
      return f"SELECT * FROM {table};"
    elif operation == "INSERT":
      return f"INSERT INTO {table} (name, email) VALUES ('test', 'test@example.com');"
    elif operation == "UPDATE":
      return f"UPDATE {table} SET name = 'updated' WHERE id = 1;"
    elif operation == "DELETE":
      return f"DELETE FROM {table} WHERE id = 1;"
    return ""

  def execute_sql(self, sql: str) -> Dict[str, Any]:
    """Execute SQL query on Supabase"""
    if not self.supabase:
      return {"success": False, "error": "Supabase not configured"}

    try:
      # Parse table name
      table_match = re.search(r'FROM\s+(\w+)|INTO\s+(\w+)|UPDATE\s+(\w+)', sql, re.IGNORECASE)
      if not table_match:
        return {"success": False, "error": "Could not find table name"}

      table_name = next(filter(None, table_match.groups()))

      # Execute based on operation type
      if sql.upper().startswith('SELECT'):
        result = self.supabase.table(table_name).select('*').limit(5).execute()
      elif sql.upper().startswith('INSERT'):
        # Simple insert for testing
        result = self.supabase.table(table_name).insert({
          "name": "test_user",
          "email": "test@example.com"
        }).execute()
      elif sql.upper().startswith('UPDATE'):
        result = self.supabase.table(table_name).update({
          "name": "updated_user"
        }).eq('id', 1).execute()
      elif sql.upper().startswith('DELETE'):
        result = self.supabase.table(table_name).delete().eq('id', 1).execute()
      else:
        return {"success": False, "error": "Unsupported operation"}

      return {
        "success": True,
        "data": result.data,
        "count": len(result.data) if result.data else 0
      }

    except Exception as e:
      return {"success": False, "error": str(e)}

  def process(self, flask_code: str, execute: bool = False) -> Dict[str, Any]:
    """Main processing function"""
    print(f"🔍 Processing Flask code...")

    # Extract SQL
    queries = self.extract_sql(flask_code)
    print(f"📊 Found {len(queries)} SQL operations")

    results = []
    if execute and queries:
      print("🚀 Executing queries...")
      for query in queries:
        result = self.execute_sql(query['sql'])
        results.append({
          "query": query,
          "result": result
        })
        status = "✅" if result['success'] else "❌"
        print(f"   {status} {query['type']}: {result.get('error', 'Success')}")

    return {
      "queries": queries,
      "execution_results": results,
      "summary": f"Found {len(queries)} queries, executed {len(results)}"
    }


# Example usage
def main():
  # Test with your Flask code
  your_flask_code = """
    @app.route('/users', methods=['POST'])
    def create_user():
        user_data = {'name': 'test', 'email': 'test@example.com'}
        response = supabase.table(USERS_TABLE).insert(user_data).execute()
        return jsonify(response.data)

    @app.route('/users', methods=['GET'])
    def get_all_users():
        query = supabase.table(USERS_TABLE).select("*")
        if limit:
            query = query.limit(limit)
        response = query.execute()
        return jsonify(response.data)

    @app.route('/users/<user_id>', methods=['GET'])
    def get_user(user_id):
        response = supabase.table(USERS_TABLE).select("*").eq('id', user_id).execute()
        return jsonify(response.data)

    @app.route('/users/<user_id>', methods=['DELETE'])
    def delete_user(user_id):
        response = supabase.table(USERS_TABLE).delete().eq('id', user_id).execute()
        return jsonify({'message': 'User deleted'})
    """

  # Initialize extractor
  extractor = SimpleFlaskSQLExtractor()

  # Process code (extract only)
  result = extractor.process(your_flask_code, execute=False)

  print("\n📋 Results:")
  for i, query in enumerate(result['queries'], 1):
    print(f"   {i}. {query['type']} on {query['table']}")
    print(f"      SQL: {query['sql']}")

  print(f"\n📊 Total operations found: {len(result['queries'])}")
  print(f"📝 Summary: {result['summary']}")

  # Uncomment to execute on real database:
  # result = extractor.process(your_flask_code, execute=True)


if __name__ == "__main__":
  main()