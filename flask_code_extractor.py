import os
import ast
import json
from typing import Dict, List, Any, Tuple, Optional

def extract_route_info(decorator: ast.Call) -> Tuple[Optional[str], List[str]]:
    """
    Extract route path and HTTP methods from a Flask route decorator.
    
    Args:
        decorator: AST Call node representing a Flask route decorator
        
    Returns:
        Tuple of (route_path, methods)
    """
    route_path = None
    methods = ['GET']  # default method if none specified
    
    # Extract route path from args
    if decorator.args:
        if isinstance(decorator.args[0], ast.Constant):
            route_path = decorator.args[0].value
        elif isinstance(decorator.args[0], ast.Str):  # for Python < 3.8
            route_path = decorator.args[0].s
        
    # Extract methods if specified in keywords
    for keyword in decorator.keywords:
        if keyword.arg == 'methods':
            if isinstance(keyword.value, ast.List):
                methods = []
                for elt in keyword.value.elts:
                    if isinstance(elt, ast.Str):  # Python < 3.8
                        methods.append(elt.s)
                    elif isinstance(elt, ast.Constant):  # Python >= 3.8
                        methods.append(elt.value)
            
    return route_path, methods

def is_flask_route_decorator(node: ast.Call) -> bool:
    """
    Check if an AST node is a Flask route decorator.
    
    This looks for patterns like:
    - @app.route()
    - @blueprint.route()
    - @app.get()
    - @app.post(), etc.
    
    Args:
        node: AST Call node to check
        
    Returns:
        Boolean indicating if this is a Flask route decorator
    """
    if not isinstance(node, ast.Call):
        return False
        
    # Check for app.route, blueprint.route pattern
    if hasattr(node.func, 'attr') and hasattr(node.func, 'value'):
        # Common HTTP method decorators
        http_methods = ['route', 'get', 'post', 'put', 'delete', 'patch', 'options', 'head']
        if node.func.attr in http_methods:
            return True
    
    return False

def extract_routes_from_file(filepath: str) -> Dict[str, Dict[str, str]]:
    """
    Extract all Flask routes from a Python file.
    
    Args:
        filepath: Path to the Python file
        
    Returns:
        Dictionary mapping route paths to methods and their code
    """
    routes = {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            source_code = file.read()
            
        tree = ast.parse(source_code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and is_flask_route_decorator(decorator):
                        try:
                            route_path, methods = extract_route_info(decorator)
                            
                            # For method-specific decorators like @app.get(), infer the method
                            if hasattr(decorator.func, 'attr'):
                                method_attr = decorator.func.attr.upper()
                                if method_attr in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']:
                                    methods = [method_attr]
                            
                            if route_path:
                                func_source = ast.get_source_segment(source_code, node)
                                
                                # Initialize route in dictionary if it doesn't exist
                                if route_path not in routes:
                                    routes[route_path] = {}
                                
                                # Add each method with its code
                                for method in methods:
                                    routes[route_path][method] = func_source
                                        
                        except Exception as e:
                            print(f"Error extracting route in {filepath} for function {node.name}: {e}")
    
    except Exception as e:
        print(f"Error reading or parsing {filepath}: {e}")
    
    return routes

def parse_flask_codebase(directory: str) -> Dict[str, Dict[str, str]]:
    """
    Parse all Python files in a directory to extract Flask routes.
    
    Args:
        directory: Path to the Flask project directory
        
    Returns:
        Dictionary mapping route paths to methods and their code
    """
    flask_routes = {}
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    routes = extract_routes_from_file(file_path)
                    for route, methods_dict in routes.items():
                        if route not in flask_routes:
                            flask_routes[route] = {}
                        
                        # Merge methods from this file
                        for method, code in methods_dict.items():
                            flask_routes[route][method] = code
                            
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")
    
    return flask_routes

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = input("Enter the path to your Flask codebase: ")
    
    routes_info = parse_flask_codebase(directory)
    
    # Output to JSON file
    output_file = "flask_routes.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(routes_info, f, indent=4)
    
    print(f"Found {len(routes_info)} routes.")
    print(f"Results saved to {output_file}")
    
    # Print a summary
    print("\nRoutes summary:")
    for route, methods_dict in routes_info.items():
        methods_str = ', '.join(methods_dict.keys())
        print(f"{methods_str.ljust(20)} {route}")