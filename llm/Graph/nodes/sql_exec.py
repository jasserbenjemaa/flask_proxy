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
# If they don't exist, you'll need to create them or adjust the imports
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
    method: Optional[str]  # Added HTTP method support
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
        in_string = False
        quote_char = None

        lines = text.split('\n')
        for line in lines:
            line = line.strip()

            # Skip empty lines and pure comment lines
            if not line or line.startswith('--'):
                continue

            # Better comment handling that respects string literals
            cleaned_line = ""
            i = 0
            while i < len(line):
                char = line[i]

                if not in_string and char in ["'", '"']:
                    in_string = True
                    quote_char = char
                    cleaned_line += char
                elif in_string and char == quote_char:
                    if i + 1 < len(line) and line[i + 1] == quote_char:  # Escaped quote
                        cleaned_line += char + char
                        i += 1
                    else:
                        in_string = False
                        quote_char = None
                        cleaned_line += char
                elif not in_string and char == '-' and i + 1 < len(line) and line[i + 1] == '-':
                    # Found comment outside string, ignore rest of line
                    break
                else:
                    cleaned_line += char
                i += 1

            line = cleaned_line.strip()
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
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-04-17",
            google_api_key=api_key,
        )

        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """Convert Flask + Supabase operations to SQL based on HTTP method and code analysis.

HTTP Method Guidelines:
- GET: Generate SELECT queries
- POST: Generate INSERT queries  
- PUT/PATCH: Generate UPDATE queries
- DELETE: Generate DELETE queries

Tasks:
- Analyze the HTTP method to determine SQL operation type
- Convert supabase.table() operations to appropriate SQL queries
- Extract table schemas from insert/update operations
- Convert filters (.eq, .neq, etc.) to WHERE clauses
- Convert .order() and .limit() to SQL equivalents
- If you see time-related functions like datetime.now(), get_current_time(), etc., note them for replacement
- Consider URL parameters for filtering (e.g., /users/123 suggests WHERE id = 123)

Output format:
## Database Schema
[CREATE TABLE statements if needed]

## SQL Queries  
[Generated SQL based on HTTP method with brief comments]

Method-specific behavior:
- GET: Focus on SELECT with appropriate WHERE clauses
- POST: Focus on INSERT with provided data
- PUT/PATCH: Focus on UPDATE with WHERE clauses
- DELETE: Focus on DELETE with WHERE clauses

Focus only on database operations that match the HTTP method."""),
            ("human", "HTTP Method: {method}\nExtract SQL from this code:\n\n{flask_code}")
        ])

        self.integration_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a SQL integration expert. Your task is to merge extracted SQL queries with client request data, URL information, HTTP method, and time functions.

Given:
1. HTTP Method (GET, POST, PUT, PATCH, DELETE)
2. Base SQL queries extracted from Flask code
3. Client request data (JSON format)
4. URL information (if provided)
5. Available time functions and their current values

HTTP Method Behavior:
- GET: Use client data for filtering, URL for specific resource IDs
- POST: Use client data as INSERT values
- PUT/PATCH: Use client data as UPDATE SET values, URL for WHERE conditions
- DELETE: Use URL for WHERE conditions, ignore most client data

Your job:
- Generate SQL that matches the HTTP method intent
- Integrate the client data appropriately based on method:
  * GET: Client data becomes WHERE conditions
  * POST: Client data becomes INSERT VALUES
  * PUT/PATCH: Client data becomes SET values
  * DELETE: Focus on WHERE conditions from URL
- Extract parameters from URL (like user_id, resource_id, etc.)
- Replace placeholders with actual values from client request and URL
- Replace any time-related function calls with actual timestamp values
- Generate clean, executable SQL statements
- Handle proper data types and constraints
- IMPORTANT: If you need user_id or any ID parameter, extract it from the provided URL path

Method-specific examples:
- GET /users/123 → SELECT * FROM users WHERE id = 123;
- POST /users + {"name": "John"} → INSERT INTO users (name) VALUES ('John');
- PUT /users/123 + {"name": "John"} → UPDATE users SET name = 'John' WHERE id = 123;
- DELETE /users/123 → DELETE FROM users WHERE id = 123;

Available time functions:
- current_time: {current_time}
- current_timestamp: {current_timestamp}
- current_iso_time: {current_iso_time}
- current_date: {current_date}

Return clean, executable SQL statements without markdown formatting."""),
            ("human", """HTTP Method: {method}

Base SQL Queries:
{extracted_sql}

Client Request Data:
{client_request}

URL Information:
{url}

Table name: {table_name}

Please integrate the client data, URL parameters, and time values into the SQL queries based on the HTTP method. 

Method-specific instructions:
- If GET: Use client data for filtering, URL for specific IDs
- If POST: Use client data as INSERT values
- If PUT/PATCH: Use client data as UPDATE SET values, URL for WHERE
- If DELETE: Use URL for WHERE conditions

Remember: if you need user_id or any ID, extract it from the URL. Use provided time values for datetime operations. Return only clean SQL statements.""")
        ])

    def extract_sql_from_flask(self, flask_code: str, method: str = "GET") -> str:
        """Use LLM to extract SQL queries from Flask Supabase code with HTTP method context"""
        try:
            if not flask_code.strip():
                return "Error: No Flask code provided"
            
            messages = self.extraction_prompt.format_messages(
                method=method.upper(),
                flask_code=flask_code
            )
            response = self.llm.invoke(messages)
            
            if not response or not hasattr(response, 'content'):
                return "Error: Invalid response from LLM"
            
            return response.content
        except Exception as e:
            return f"Error extracting SQL: {str(e)}"

    def integrate_client_request(self, extracted_sql: str, client_request: Dict[str, Any],
                                 url: Optional[str] = None, table_name: str = "", method: str = "GET") -> str:
        """Integrate client request data and URL with extracted SQL queries based on HTTP method"""
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
                method=method.upper(),
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
    """Node to extract SQL queries from Flask Supabase code using LLM with HTTP method"""
    try:
        if not state.get("flask_code", "").strip():
            return {
                "extracted_sql": "",
                "error": "No Flask code provided"
            }

        analyzer = SupabaseCodeAnalyzer()
        method = state.get("method", "GET")
        extracted_sql = analyzer.extract_sql_from_flask(state["flask_code"], method)

        # Check if extraction returned an error
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
    """Node to integrate client request data with extracted SQL based on HTTP method"""
    try:
        # If no client request, just pass through the extracted SQL
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
        method = state.get("method", "GET")
        integrated_sql = analyzer.integrate_client_request(
            extracted_sql,
            state.get("client_request", {}),
            state.get("url"),
            state.get("table_name", ""),
            method
        )

        # Check if integration returned an error
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
    if state.get("error"):
        return "error"
    if not state.get("extracted_sql", "").strip():
        return "no_sql"
    return "integrate"


def should_continue_integration(state: SQLExtractorState) -> str:
    """Determine if workflow should continue after integration"""
    if state.get("error"):
        return "error"
    return "clean"


def should_continue_cleaning(state: SQLExtractorState) -> str:
    """Determine if workflow should continue after cleaning"""
    if state.get("error"):
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


# Enhanced usage functions with method support
def process_flask_supabase_code_with_client_request(
    flask_code: str,
    table_name: str,
    client_request: Optional[Dict[str, Any]] = None,
    url: Optional[str] = None,
    method: str = "GET"
) -> Dict[str, Any]:
    """Process Flask + Supabase code with optional client request, URL, and HTTP method through the enhanced workflow"""
    try:
        # Create the workflow
        app = create_enhanced_sql_extractor_graph()

        # Initialize state
        initial_state: SQLExtractorState = {
            "flask_code": flask_code,
            "client_request": client_request,
            "table_name": table_name,
            "url": url,
            "method": method.upper(),
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
            "method": result.get("method"),
            "extracted_sql": result["extracted_sql"],
            "integrated_sql": result["integrated_sql"],
            "cleaned_sql": result["cleaned_sql"],
            "error": result["error"]
        }
    except Exception as e:
        return {
            "original_code": flask_code,
            "client_request": client_request,
            "url": url,
            "method": method,
            "extracted_sql": "",
            "integrated_sql": "",
            "cleaned_sql": "",
            "error": f"Workflow execution error: {str(e)}"
        }


def process_with_client_query(flask_code: str, table_name: str, client_req: Dict[str, Any], 
                             url: Optional[str] = None, method: str = "GET") -> Dict[str, Any]:
    """Convenience function specifically for processing with client queries, URL, and HTTP method"""
    return process_flask_supabase_code_with_client_request(flask_code, table_name, client_req, url, method)


def process_without_client_query(flask_code: str, table_name: str, url: Optional[str] = None, 
                                method: str = "GET") -> Dict[str, Any]:
    """Convenience function for processing without client queries but with optional URL and HTTP method"""
    return process_flask_supabase_code_with_client_request(flask_code, table_name, None, url, method)


# Example usage
def sql_exec(state: GraphState) -> Dict[str, Any]:
    """Main execution function for the SQL extraction and execution pipeline with HTTP method support"""
    sample_flask_supabase_code = state.get("code", "")
    client_request = state.get("client_req", {})
    url = state.get("url", "")
    table_name = state.get("table_name", "")
    method = state.get("method", "GET")  # Added method support

    # Validate inputs
    if not sample_flask_supabase_code.strip():
        return {
            "sqls_result": state.get("sqls_result", []),
            "funcs_result": {},
            "error": "No Flask code provided"
        }

    # Create proper SQLExtractorState for functions
    functions_state: SQLExtractorState = {
        "flask_code": sample_flask_supabase_code,
        "table_name": table_name,
        "client_request": client_request,
        "url": url,
        "method": method,
        "extracted_sql": "",
        "integrated_sql": "",
        "cleaned_sql": "",
        "error": ""
    }
    functions_result = execute_functions_node(functions_state)

    try:
        # Step 1: Run your SQL extraction workflow with method support
        result_with_client = process_with_client_query(sample_flask_supabase_code, table_name, client_request, url, method)

        # Validate result
        if result_with_client.get('error'):
            return {
                "sqls_result": state.get("sqls_result", []),
                "funcs_result": functions_result.get("functions_result", {}),
                "error": result_with_client['error']
            }

        # Step 2: Print the integrated SQL
        print("\n" + "=" * 60)
        print(f"INTEGRATED SQL WITH CLIENT DATA AND URL (Method: {method}):")
        print("=" * 60)
        print(result_with_client.get('integrated_sql', 'No integrated SQL'))

        # Step 2.5: Print the cleaned SQL
        print("\n" + "=" * 60)
        print("CLEANED SQL FOR EXECUTION:")
        print("=" * 60)
        print(result_with_client.get('cleaned_sql', 'No cleaned SQL'))

        # Step 3: Execute the cleaned SQL using your executor
        if result_with_client.get('cleaned_sql'):
            execution_result = execute_extracted_sql({
                **result_with_client,
                'integrated_sql': result_with_client['cleaned_sql']
            })
        else:
            execution_result = {"success": False, "error": "No valid SQL to execute"}

        # Step 4: Print execution outcome
        error = None
        print("\n" + "=" * 60)
        print("EXECUTION RESULT")
        print("=" * 60)
        if execution_result.get("success"):
            print("✅ Execution successful!")
            print("📦 Data:", execution_result.get("data"))
        else:
            error = execution_result.get("error", "Unknown execution error")
            print("❌ Execution failed:", error)

        # Prepare results
        sql_results = state.get("sqls_result", [])
        if execution_result.get('data'):
            sql_results.append(execution_result.get('data'))

        return {
            "sqls_result": sql_results,
            "funcs_result": functions_result.get("functions_result", {}),
            "error": error,
        }

    except Exception as e:
        return {
            "sqls_result": state.get("sqls_result", []),
            "funcs_result": functions_result.get("functions_result", {}),
            "error": f"Unexpected error in sql_exec: {str(e)}"
        }


# Additional utility functions for testing and debugging with method support
def test_sql_extraction_with_method(flask_code: str, table_name: str = "test_table", 
                                   method: str = "GET", url: str = None, 
                                   client_data: Dict[str, Any] = None) -> None:
    """Test function to verify SQL extraction works correctly with HTTP method"""
    print(f"Testing SQL Extraction with Method: {method}")
    print("=" * 50)
    
    try:
        if client_data:
            result = process_with_client_query(flask_code, table_name, client_data, url, method)
        else:
            result = process_without_client_query(flask_code, table_name, url, method)
        
        print(f"HTTP Method: {method}")
        print(f"URL: {url or 'Not provided'}")
        print(f"Client Data: {client_data or 'Not provided'}")
        print("\nOriginal Code:")
        print(flask_code)
        print("\nExtracted SQL:")
        print(result.get('extracted_sql', 'No SQL extracted'))
        print("\nIntegrated SQL:")
        print(result.get('integrated_sql', 'No integrated SQL'))
        print("\nCleaned SQL:")
        print(result.get('cleaned_sql', 'No cleaned SQL'))
        
        if result.get('error'):
            print(f"\nError: {result['error']}")
        else:
            print("\n✅ Test completed successfully!")
            
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")


if __name__ == "__main__":
    # Example usage with different HTTP methods
    sample_code = """
    from supabase import create_client
    
    def manage_user_posts(user_id):
        supabase = create_client(url, key)
        result = supabase.table('posts').select('*').eq('user_id', user_id).execute()
        return result.data
    """
    
    # Test with different methods
    print("Testing GET method:")
    test_sql_extraction_with_method(sample_code, "posts", "GET", "/posts/123")
    
    print("\n" + "="*60 + "\n")
    
    print("Testing POST method:")
    test_sql_extraction_with_method(sample_code, "posts", "POST", "/posts", 
                                   {"title": "New Post", "content": "Hello World", "user_id": 123})
    
    print("\n" + "="*60 + "\n")
    
    print("Testing DELETE method:")
    test_sql_extraction_with_method(sample_code, "posts", "DELETE", "/posts/123")