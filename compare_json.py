import json
from collections import defaultdict
import difflib



def compare_json_keys(a, b, path=""):
    """
    Recursively compares the keys of two JSON structures.
    Returns paths of keys that are missing in one of them.
    
    :param a: First JSON object
    :param b: Second JSON object
    :param path: Current path in the tree (for internal use)
    :return: Dictionary showing which keys are missing and where
    """
    mismatches = {}

    if isinstance(a, dict) and isinstance(b, dict):
        all_keys = set(a.keys()).union(b.keys())
        for key in all_keys:
            new_path = f"{path}.{key}" if path else key
            if key not in a:
                mismatches[new_path] = "Missing in A"
            elif key not in b:
                mismatches[new_path] = "Missing in B"
            else:
                # Recursive check
                mismatches.update(compare_json_keys(a[key], b[key], new_path))

    elif isinstance(a, list) and isinstance(b, list):
        # For list elements, just compare the first element as schema
        if a and b:
            mismatches.update(compare_json_keys(a[0], b[0], f"{path}[0]"))
        elif a and not b:
            mismatches[f"{path}[0]"] = "Missing in B"
        elif b and not a:
            mismatches[f"{path}[0]"] = "Missing in A"
    else:
        # If one is dict/list and the other is not, that’s a structural mismatch
        if type(a) != type(b):
            mismatches[path] = f"Type mismatch: {type(a).__name__} vs {type(b).__name__}"

    return mismatches

json_a = {
    "user": {
        "id": 123,
        "name": {
            "first": "Alice",
            "thirds": "Alice",
            "first888": "Alice",
            "last": "Johnson"
        },
        "address": {
            "street": "123 Main St",
            "city": "Springfield",
            "zipcode": "12345"
        },
        "emails": [
            {"type": "work", "email": "alice@company.com"},
            {"type": "personal", "email": "alice@gmail.com"}
        ],
        "preferences": {
            "newsletter": True,
            "notifications": {
                "email": True,
                "sms": False
            }
        }
    },
    "session": {
        "token": "abc123",
        "expires": "2025-01-01T00:00:00Z"
    }
}

json_b = {
    "user": {
        "id": 123,
        "name": {
            "firsts": "Alice",
            "third": "Alice",
            "second": "Alice",
            "last": "Johnson"
            # Missing "last"
        },
        "address": {
            "street": "123 Main St",
            "zipcode": "12345",
            "country": "USA"  # Extra key
        },
        "emails": [
            {"type": "work", "email": "alice@company.com", "verified": True}
        ],
        "preferences": {
            "newsletter": False
            # Missing "notifications"
        }
    },
    "session": {
        "token": "abc123"
        # Missing "expires"
    },
    "device": {
        "type": "mobile",
        "os": "iOS"
    }
}


def compare_words(word1, word2):
    """
    Compare two words using sequence similarity.
    
    :param word1: First word
    :param word2: Second word
    :return: Similarity ratio (float between 0 and 1)
    """
    return round(difflib.SequenceMatcher(None, word1, word2).ratio(), 3)



def finall_boss_improved(obj):
    """
    Improved version with clearer logic and better variable names.
    
    :param obj: Dictionary with field paths as keys and "Missing in A"/"Missing in B" as values
    :return: List of match tuples (a_path, b_path, score)
    """
    matches = []
    
    for a_key, a_value in obj.items():
        if a_value == "Missing in A":
            a_path = ".".join(a_key.split(".")[:-1])  # Base path
            a_field = a_key.split(".")[-1]            # Field name
            
            best_match = None
            best_score = 0
            
            for b_key, b_value in obj.items():
                if b_value == "Missing in B":
                    b_path = ".".join(b_key.split(".")[:-1])
                    b_field = b_key.split(".")[-1]
                    
                    # Only compare fields with the same base path
                    if b_path == a_path:
                        score = compare_words(a_field, b_field)
                        
                        if score > best_score:
                            best_score = score
                            best_match = b_key
            
            if best_match:
                matches.append((a_key, best_match, best_score))
                
    # Sort by score (highest first)
    matches.sort(key=lambda x: x[2], reverse=True)
    
    # Print matches
    for a_key, b_key, score in matches:
        print(f"{b_key} ↔ {a_key} (score: {score})")
        
    return matches




differences = compare_json_keys(json_a, json_b)
print(json.dumps(differences, indent=4))
print("\nImproved approach:")
finall_boss_improved(differences)
