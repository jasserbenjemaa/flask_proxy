#!/usr/bin/env python3
"""
Python Function Extractor
Extracts all function definitions from Python files in a repository.
"""

import ast
import os
import argparse
import json
from pathlib import Path
from typing import List, Dict, Tuple


class FunctionExtractor:
    def __init__(self):
        self.functions = []
    
    def extract_functions_from_file(self, file_path: str) -> List[Dict]:
        """Extract all functions from a single Python file."""
        functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Parse the file into an AST
            tree = ast.parse(content, filename=file_path)
            
            # Walk through all nodes in the AST
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = self._extract_function_info(node, file_path, content)
                    functions.append(func_info)
                elif isinstance(node, ast.AsyncFunctionDef):
                    func_info = self._extract_function_info(node, file_path, content, is_async=True)
                    functions.append(func_info)
        
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Error parsing {file_path}: {e}")
        
        return functions
    
    def _extract_function_info(self, node: ast.FunctionDef, file_path: str, content: str, is_async: bool = False) -> Dict:
        """Extract detailed information about a function."""
        lines = content.split('\n')
        
        # Get function signature
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        # Handle default arguments
        defaults = []
        if node.args.defaults:
            for default in node.args.defaults:
                try:
                    defaults.append(ast.unparse(default))
                except:
                    defaults.append("<unparseable>")
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        # Get decorators
        decorators = []
        for decorator in node.decorator_list:
            try:
                decorators.append(ast.unparse(decorator))
            except:
                decorators.append("<unparseable>")
        
        # Determine if it's a method (inside a class)
        is_method = False
        class_name = None
        for parent in ast.walk(ast.parse(content)):
            if isinstance(parent, ast.ClassDef):
                for child in ast.walk(parent):
                    if child is node:
                        is_method = True
                        class_name = parent.name
                        break
        
        return {
            'name': node.name,
            'file': file_path,
            'line_number': node.lineno,
            'is_async': is_async,
            'is_method': is_method,
            'class_name': class_name,
            'arguments': args,
            'defaults': defaults,
            'decorators': decorators,
            'docstring': docstring,
            'source_lines': (node.lineno, node.end_lineno)
        }
    
    def extract_from_directory(self, directory: str, recursive: bool = True) -> List[Dict]:
        """Extract functions from all Python files in a directory."""
        all_functions = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"Directory {directory} does not exist")
            return all_functions
        
        # Find all Python files
        if recursive:
            python_files = directory_path.rglob("*.py")
        else:
            python_files = directory_path.glob("*.py")
        
        for file_path in python_files:
            print(f"Processing: {file_path}")
            functions = self.extract_functions_from_file(str(file_path))
            all_functions.extend(functions)
        
        return all_functions
    
    def save_to_file(self, functions: List[Dict], output_file: str, format_type: str = 'json'):
        """Save extracted functions to a file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            if format_type == 'json':
                # Create function dictionary with function names as keys
                functions_dict = {}
                for func in functions:
                    func_key = func['name']
                    
                    # Handle duplicate function names by adding class name or file info
                    if func_key in functions_dict:
                        if func['class_name']:
                            func_key = f"{func['class_name']}.{func['name']}"
                        else:
                            # Use filename if no class name
                            filename = os.path.basename(func['file']).replace('.py', '')
                            func_key = f"{filename}.{func['name']}"
                        
                        # If still duplicate, add line number
                        if func_key in functions_dict:
                            func_key = f"{func_key}_line{func['line_number']}"
                    
                    functions_dict[func_key] = func
                
                # Create structured JSON output with functions as top-level keys
                output_data = {
                    'metadata': {
                        'total_functions': len(functions),
                        'regular_functions': sum(1 for f in functions if not f['is_async'] and not f['is_method']),
                        'methods': sum(1 for f in functions if f['is_method']),
                        'async_functions': sum(1 for f in functions if f['is_async']),
                        'files_processed': len(set(f['file'] for f in functions))
                    },
                    'functions': functions_dict
                }
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            elif format_type == 'simple':
                for func in functions:
                    f.write(f"{func['file']}:{func['line_number']} - {func['name']}\n")
            
            elif format_type == 'detailed':
                for i, func in enumerate(functions):
                    f.write(f"Function #{i+1}\n")
                    f.write(f"Name: {func['name']}\n")
                    f.write(f"File: {func['file']}\n")
                    f.write(f"Line: {func['line_number']}\n")
                    f.write(f"Type: {'Async ' if func['is_async'] else ''}{'Method' if func['is_method'] else 'Function'}\n")
                    
                    if func['class_name']:
                        f.write(f"Class: {func['class_name']}\n")
                    
                    if func['arguments']:
                        f.write(f"Arguments: {', '.join(func['arguments'])}\n")
                    
                    if func['decorators']:
                        f.write(f"Decorators: {', '.join(func['decorators'])}\n")
                    
                    if func['docstring']:
                        f.write(f"Docstring: {func['docstring'][:100]}{'...' if len(func['docstring']) > 100 else ''}\n")
                    
                    f.write("-" * 50 + "\n\n")
    
    def print_summary(self, functions: List[Dict]):
        """Print a summary of extracted functions."""
        if not functions:
            print("No functions found.")
            return
        
        print(f"\nFound {len(functions)} functions:")
        print(f"Regular functions: {sum(1 for f in functions if not f['is_async'] and not f['is_method'])}")
        print(f"Methods: {sum(1 for f in functions if f['is_method'])}")
        print(f"Async functions: {sum(1 for f in functions if f['is_async'])}")
        
        # Group by file
        files = {}
        for func in functions:
            if func['file'] not in files:
                files[func['file']] = 0
            files[func['file']] += 1
        
        print(f"\nFunctions per file:")
        for file, count in sorted(files.items()):
            print(f"  {file}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Extract Python functions from a repository")
    parser.add_argument("path", help="Path to repository or Python file")
    parser.add_argument("--output", "-o", help="Output file to save results")
    parser.add_argument("--format", choices=['simple', 'detailed', 'json'], default='json',
                       help="Output format (default: json)")
    parser.add_argument("--no-recursive", action='store_true',
                       help="Don't search subdirectories recursively")
    
    args = parser.parse_args()
    
    extractor = FunctionExtractor()
    
    # Check if path is a file or directory
    if os.path.isfile(args.path):
        functions = extractor.extract_functions_from_file(args.path)
    else:
        functions = extractor.extract_from_directory(args.path, recursive=not args.no_recursive)
    
    # Print summary
    extractor.print_summary(functions)
    
    # Save to file if requested
    if args.output:
        extractor.save_to_file(functions, args.output, args.format)
        print(f"\nResults saved to {args.output}")
    
    # Print first few functions as preview
    if functions:
        print(f"\nFirst few functions:")
        for func in functions[:5]:
            type_str = "async " if func['is_async'] else ""
            type_str += "method" if func['is_method'] else "function"
            class_str = f" (in {func['class_name']})" if func['class_name'] else ""
            print(f"  {func['name']} - {type_str}{class_str} at {func['file']}:{func['line_number']}")


if __name__ == "__main__":
    main()