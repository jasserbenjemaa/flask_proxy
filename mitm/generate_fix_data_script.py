def generate_fix_data_script(field_similarity_tuples,file_path):
  
    # Generate the assignment statements for the fix_data function
    assignment_statements = []
    
    for incorrect_path, correct_path, similarity in field_similarity_tuples:
        # Parse the field paths
        incorrect_parts = incorrect_path.split('.')
        correct_parts = correct_path.split('.')
        
        # Generate the correct path accessor
        correct_accessor = "data"
        for part in correct_parts[:-1]:  # All parts except the last one
            correct_accessor += f"['{part}']"
        correct_accessor += f"['{correct_parts[-1]}']"
        
        # Generate the incorrect path accessor
        incorrect_accessor = "data"
        for part in incorrect_parts[:-1]:  # All parts except the last one
            incorrect_accessor += f"['{part}']"
        incorrect_accessor += f"['{incorrect_parts[-1]}']"
        
        # Create the assignment statement with safety check to avoid errors if incorrect path doesn't exist
        assignment = f"""    # Similarity score: {similarity:.3f}
    try:
        if '{incorrect_parts[-1]}' in {incorrect_accessor.rsplit('[', 1)[0]}:
            {correct_accessor} = {incorrect_accessor}
            # Optional: remove the incorrect field after copying its value
            del {incorrect_accessor.rsplit('[', 1)[0]}['{incorrect_parts[-1]}']
    except (KeyError, TypeError):
        pass"""
        assignment_statements.append(assignment)
    
    # Join all assignments with newlines
    assignments_block = "\n\n".join(assignment_statements)
    
    # Create the full script with better error handling and documentation
    script = f"""
#!/usr/bin/env python3
import sys
import json

def fix_data(data):
{assignments_block}
    return data

def get_nested_value(data, path_parts):
    
    current = data
    for part in path_parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current

def set_nested_value(data, path_parts, value):
    
    current = data
    for part in path_parts[:-1]:
        if part not in current:
            current[part] = {{}}
        current = current[part]
    current[path_parts[-1]] = value

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py '<json_string>'")
        sys.exit(1)
        
    input_data = sys.argv[1]
    try:
        data = json.loads(input_data)
        fixed_data = fix_data(data)
        print(json.dumps(fixed_data, indent=2))
    except json.JSONDecodeError:
        print("Error: Invalid JSON format.")
"""
    
    with open(file_path, 'w') as f:
         f.write(script)
    #return script


# Example usage with more robust error handling
if __name__ == "__main__":
    # Example array of field similarity tuples
    # Format: (incorrect_field_path, correct_field_path, similarity_score)
    array = [
        ('name.firt_name', 'name.first_name', 0.947),
        ('sourc', 'source', 0.909),
        ('name.secd_name', 'name.second_name', 0.9),
        ('addrss.street', 'address.street', 0.93),
        ('contct.phone', 'contact.phone', 0.89)
    ]
    
    # Generate the script
    
    # Optional: Save the script to a file