import ast
import os
import json
import re
from typing import Dict, List, Any, Optional

class FunctionParser:
    def __init__(self):
        self.functions = {}
    
    def parse_file(self, file_path: str) -> None:
        """Parse a single Python file and extract function information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Parse the AST
            tree = ast.parse(content)
            
            # Extract functions from the AST
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = self._extract_function_info(node, content)
                    if func_info:
                        self.functions[func_info['name']] = func_info['details']
                        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
    
    def _extract_function_info(self, node: ast.FunctionDef, content: str) -> Optional[Dict]:
        """Extract detailed information from a function node."""
        try:
            # Check if this is a Flask endpoint function (has @app.route decorator)
            if self._is_flask_endpoint(node):
                return None  # Skip Flask endpoint functions
            
            # Get function name
            name = node.name
            
            # Extract docstring/description
            description = self._extract_docstring(node)
            
            # Extract parameters
            parameters = self._extract_parameters(node)
            
            # Extract return type annotation
            returns = self._extract_return_type(node)
            
            # Extract the actual code
            code = self._extract_function_code(node, content)
            
            return {
                'name': name,
                'details': {
                    'description': description,
                    'code': code,
                    'parameters': parameters,
                    'returns': returns
                }
            }
        except Exception as e:
            print(f"Error extracting function info for {node.name}: {e}")
            return None
    
    def _is_flask_endpoint(self, node: ast.FunctionDef) -> bool:
        """Check if a function is a Flask endpoint (decorated with @app.route) or error handler."""
        for decorator in node.decorator_list:
            # Handle @app.route
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (isinstance(decorator.func.value, ast.Name) and 
                        decorator.func.value.id == 'app' and 
                        decorator.func.attr in ['route', 'errorhandler', 'before_request', 'after_request', 'teardown_request']):
                        return True
            
            # Handle @app.route without parentheses (less common but possible)
            elif isinstance(decorator, ast.Attribute):
                if (isinstance(decorator.value, ast.Name) and 
                    decorator.value.id == 'app' and 
                    decorator.attr in ['route', 'errorhandler', 'before_request', 'after_request', 'teardown_request']):
                    return True
            
            # Handle blueprint routes like @bp.route, @bp.errorhandler
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr in ['route', 'errorhandler', 'before_request', 'after_request', 'teardown_request']:
                        return True
            
            elif isinstance(decorator, ast.Attribute):
                if decorator.attr in ['route', 'errorhandler', 'before_request', 'after_request', 'teardown_request']:
                    return True
        
        return False
    
    def _extract_docstring(self, node: ast.FunctionDef) -> str:
        """Extract docstring or generate a basic description."""
        if (node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            
            docstring = node.body[0].value.value.strip()
            # Return first line of docstring
            return docstring.split('\n')[0]
        
        # Generate basic description if no docstring
        return f"Function {node.name}"
    
    def _extract_parameters(self, node: ast.FunctionDef) -> List[str]:
        """Extract function parameters."""
        params = []
        
        # Regular arguments
        for arg in node.args.args:
            if arg.arg != 'self':  # Skip 'self' parameter
                params.append(arg.arg)
        
        # *args
        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")
        
        # **kwargs
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")
        
        return params
    
    def _extract_return_type(self, node: ast.FunctionDef) -> str:
        """Extract return type from type annotation or infer from code."""
        # Check for return type annotation
        if node.returns:
            return ast.unparse(node.returns)
        
        # Try to infer return type from return statements
        return_type = self._infer_return_type(node)
        return return_type if return_type else "Any"
    
    def _infer_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Infer return type from return statements."""
        return_types = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value:
                if isinstance(child.value, ast.Constant):
                    return_types.add(type(child.value.value).__name__)
                elif isinstance(child.value, ast.Dict):
                    return_types.add("dict")
                elif isinstance(child.value, ast.List):
                    return_types.add("list")
                elif isinstance(child.value, ast.Tuple):
                    return_types.add("tuple")
                elif isinstance(child.value, ast.Set):
                    return_types.add("set")
                elif isinstance(child.value, ast.Call):
                    if isinstance(child.value.func, ast.Name):
                        if child.value.func.id in ['str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple']:
                            return_types.add(child.value.func.id)
        
        if len(return_types) == 1:
            return list(return_types)[0]
        elif len(return_types) > 1:
            return "Union[" + ", ".join(sorted(return_types)) + "]"
        
        return None
    
    def _extract_function_code(self, node: ast.FunctionDef, content: str) -> str:
        """Extract the actual function code as a string."""
        try:
            # Get the source code lines
            lines = content.split('\n')
            
            # Find the function definition line
            start_line = node.lineno - 1  # AST line numbers are 1-based
            end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
            
            if end_line is None:
                # If end_line is not available, find it manually
                end_line = self._find_function_end(lines, start_line)
            
            # Extract the function code
            func_lines = lines[start_line:end_line]
            
            # Remove common indentation
            if func_lines:
                # Find minimum indentation (excluding empty lines)
                min_indent = float('inf')
                for line in func_lines:
                    if line.strip():
                        indent = len(line) - len(line.lstrip())
                        min_indent = min(min_indent, indent)
                
                if min_indent != float('inf'):
                    func_lines = [line[min_indent:] if line.strip() else line for line in func_lines]
            
            return '\n'.join(func_lines).strip()
            
        except Exception as e:
            print(f"Error extracting code for function {node.name}: {e}")
            return f"def {node.name}({', '.join(arg.arg for arg in node.args.args)}): ..."
    
    def _find_function_end(self, lines: List[str], start_line: int) -> int:
        """Find the end line of a function manually."""
        if start_line >= len(lines):
            return start_line + 1
        
        # Get the indentation of the function definition
        func_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
        
        # Find the end of the function
        current_line = start_line + 1
        while current_line < len(lines):
            line = lines[current_line]
            
            # Skip empty lines
            if not line.strip():
                current_line += 1
                continue
            
            # Check indentation
            line_indent = len(line) - len(line.lstrip())
            
            # If we find a line with equal or less indentation, function ends
            if line_indent <= func_indent:
                break
            
            current_line += 1
        
        return current_line
    
    def parse_directory(self, directory: str, recursive: bool = True) -> None:
        """Parse all Python files in a directory."""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self.parse_file(file_path)
            
            if not recursive:
                break
    
    def get_functions_json(self) -> str:
        """Return functions as JSON string."""
        return json.dumps(self.functions, indent=2, ensure_ascii=False)
    
    def save_to_file(self, output_file: str = None) -> None:
        """Save the parsed functions to a JSON file."""
        if output_file is None:
            output_file = "./llm/Graph/nodes/sample_functions.json"
        
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(self.get_functions_json())
            print(f"Results saved to {output_file}")
        except Exception as e:
            print(f"Error saving to {output_file}: {e}")
            # Try to save in current directory as fallback
            fallback_file = "sample_functions.json"
            try:
                with open(fallback_file, 'w', encoding='utf-8') as f:
                    f.write(self.get_functions_json())
                print(f"Saved to fallback location: {fallback_file}")
            except Exception as fallback_e:
                print(f"Failed to save even to fallback location: {fallback_e}")
    
    def print_summary(self) -> None:
        """Print a summary of parsed functions."""
        print(f"Found {len(self.functions)} functions:")
        for name in sorted(self.functions.keys()):
            print(f"  - {name}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse Python codebase and extract function information')
    parser.add_argument('path', help='Path to Python file or directory to parse')
    parser.add_argument('-o', '--output', default=None,
                       help='Output file path (default: flask_proxy/llm/Graph/nodes/sample_functions.json)')
    parser.add_argument('-r', '--recursive', action='store_true', default=True,
                       help='Parse directories recursively (default: True)')
    parser.add_argument('--no-recursive', action='store_true',
                       help='Disable recursive directory parsing')
    parser.add_argument('-s', '--summary', action='store_true',
                       help='Print summary of found functions')
    parser.add_argument('--stdout', action='store_true',
                       help='Print results to stdout instead of saving to file')
    
    args = parser.parse_args()
    
    # Initialize parser
    func_parser = FunctionParser()
    
    # Parse the input
    if os.path.isfile(args.path):
        print(f"Parsing file: {args.path}")
        func_parser.parse_file(args.path)
    elif os.path.isdir(args.path):
        recursive = not args.no_recursive if args.no_recursive else args.recursive
        print(f"Parsing directory: {args.path} (recursive: {recursive})")
        func_parser.parse_directory(args.path, recursive=recursive)
    else:
        print(f"Error: {args.path} is not a valid file or directory")
        return 1
    
    # Print summary if requested
    if args.summary:
        func_parser.print_summary()
    
    # Save to file or print to stdout
    if args.stdout:
        print(func_parser.get_functions_json())
    else:
        output_file = "./llm/Graph/nodes/sample_functions.json"
        func_parser.save_to_file(output_file)
    
    return 0

if __name__ == "__main__":
    exit(main())

# Example usage:
# python function_parser.py /path/to/your/codebase -s
# python function_parser.py single_file.py
# python function_parser.py /path/to/directory --no-recursive
# python function_parser.py /path/to/codebase --stdout  # Print to console instead of saving
# python function_parser.py /path/to/codebase -o custom/path/functions.json  # Custom output path