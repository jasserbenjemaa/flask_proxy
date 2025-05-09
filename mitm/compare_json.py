import json
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
        # If one is dict/list and the other is not, that's a structural mismatch
        if type(a) != type(b):
            mismatches[path] = f"Type mismatch: {type(a).__name__} vs {type(b).__name__}"

    return mismatches



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



def compare_json(json_a,json_b):
    differences = compare_json_keys(json_a, json_b)
    similarity=finall_boss_improved(differences)
    return {"similarity":similarity,"differences":differences}


# Example usage 1: Simple comparison of JSON objects with similar structure but different field names
if __name__ == "__main__":
    # Example 1: Simple objects with slightly different field names
    json_a = {
        "user": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com"
        },
        "preferences": {
            "theme": "dark",
            "notifications": True
        }
    }

    json_b = {
        "user": {
            "firstName": "Jane",
            "lastName": "Smith",
            "email": "jane@example.com",
            "phone": "555-1234"
        },
        "preferences": {
            "theme": "light",
            "notify": False
        }
    }

    print("Example 1: Simple comparison")
    result1 = compare_json(json_a, json_b)
    print("\nDifferences:", json.dumps(result1["similarity"], indent=2))
    print("\n" + "-"*50 + "\n")

    # Example 2: Nested structures with arrays
    json_a = {
        "products": [
            {
                "id": 1,
                "name": "Laptop",
                "price": 999.99,
                "specs": {
                    "cpu": "Intel i7",
                    "ram": "16GB"
                }
            }
        ],
        "metadata": {
            "count": 1,
            "page": 1
        }
    }

    json_b = {
        "products": [
            {
                "id": 2,
                "name": "Desktop",
                "price": 1499.99,
                "specs": {
                    "cpu": "AMD Ryzen",
                    "memory": "32GB",
                    "storage": "1TB SSD"
                }
            }
        ],
        "metadata": {
            "total": 1,
            "page": 1,
            "limit": 10
        }
    }

    print("Example 2: Nested structures with arrays")
    result2 = compare_json(json_a, json_b)
    print("\nDifferences:", json.dumps(result2["similarity"], indent=2))
    print("\n" + "-"*50 + "\n")

    # Example 3: Structural mismatches
    json_a = {
        "user": {
            "name": "John",
            "addresses": [
                {
                    "type": "home",
                    "street": "123 Main St"
                }
            ]
        }
    }

    json_b = {
        "user": {
            "name": "John",
            "addresses": "123 Main St"  # Not an array like in json_a
        }
    }

    print("Example 3: Structural mismatches")
    result3 = compare_json(json_a, json_b)
    print("\nDifferences:", json.dumps(result3["similarity"], indent=2))