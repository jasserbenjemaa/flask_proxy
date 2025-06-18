import requests
import json
import os
from dotenv import load_dotenv
import sys
from typing import List, Dict, Any

def send_code_to_gemini(code_snippet: str, api_key: str, endpoint_path: str = "/",
                        method: str = "POST", model: str = "gemini-2.0-flash") -> Dict[str, Any]:
    """
    Send a flask code snippet to Gemini and get sample JSON payload that correctly satisfies
    the structure expected by this endpoint.

    Args:
        code_snippet: The code snippet to send to Gemini
        api_key: Your Gemini API key
        endpoint_path: The API endpoint path (for context)
        method: HTTP method for this endpoint
        model: The Gemini model to use (default: "gemini-2.0-flash")

    Returns:
        The response from Gemini
    """
    base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    url = f"{base_url}?key={api_key}"

    # Include endpoint path and method in the prompt
    context = f"API Path: {endpoint_path}\nHTTP Method: {method}\n"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"""{context}Given the following Flask endpoint:\n\n```\n{code_snippet}\n```
                        analyze the structure of the expected JSON payload. Then, provide a
                        valid example of the JSON body that would successfully pass through this endpoint.
                        Format values as strings (like "string") or appropriate data types.
                        Only output the JSON payload — no explanation, no code comments, and no additional text."""
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.json()

def process_flask_endpoints(input_file: str, output_file: str, api_key: str, model: str = "gemini-2.0-flash") -> None:
    """
    Process Flask endpoints from a JSON file and save the Gemini responses to another file.
    The input format should be: {"/endpoint": {"GET": "code", "POST": "code"}}
    The output will be formatted with endpoint paths as keys and sample payloads as values.

    Args:
        input_file: Path to JSON file containing Flask code snippets
        output_file: Path to save the results with Gemini responses
        api_key: Your Gemini API key
        model: The Gemini model to use (default: "gemini-2.0-flash")
    """
    try:
        # Read the input JSON file
        with open(input_file, 'r') as f:
            flask_routes = json.load(f)

        # Initialize the results dictionary with endpoint paths as keys
        results = {}

        # Count total endpoints that need processing
        total_endpoints = 0
        for endpoint_path, methods_dict in flask_routes.items():
            write_methods = ["POST", "PUT", "PATCH"]
            for method in methods_dict.keys():
                if method in write_methods:
                    total_endpoints += 1

        processed = 0

        for endpoint_path, methods_dict in flask_routes.items():
            print(f"Processing endpoint: {endpoint_path}...")

            # Process each HTTP method for this endpoint
            for method, code_snippet in methods_dict.items():
                # Skip endpoints that don't accept POST/PUT/PATCH methods (typically don't need JSON payload)
                write_methods = ["POST", "PUT", "PATCH"]
                if method not in write_methods:
                    print(f"Skipping {endpoint_path} {method} as it doesn't use POST/PUT/PATCH methods...")
                    continue

                processed += 1
                print(f"Processing {processed}/{total_endpoints}: {endpoint_path} [{method}]...")

                if code_snippet and code_snippet.strip():
                    # Send the code to Gemini
                    gemini_response = send_code_to_gemini(
                        code_snippet,
                        api_key,
                        endpoint_path=endpoint_path,
                        method=method,
                        model=model
                    )

                    # Extract the response text from Gemini
                    try:
                        response_text = gemini_response["candidates"][0]["content"]["parts"][0]["text"]

                        # Format the response text to ensure it's valid JSON
                        # Strip any markdown formatting or extra text
                        response_text = response_text.strip()
                        if response_text.startswith("```json"):
                            response_text = response_text[7:]
                        if response_text.startswith("```"):
                            response_text = response_text[3:]
                        if response_text.endswith("```"):
                            response_text = response_text[:-3]
                        response_text = response_text.strip()

                        # Try to parse the JSON to validate it
                        try:
                            json_payload = json.loads(response_text)
                            
                            # Initialize endpoint in results if it doesn't exist
                            if endpoint_path not in results:
                                results[endpoint_path] = {}
                            
                            # Add the method and its payload to the endpoint
                            results[endpoint_path][method] = json_payload
                            
                        except json.JSONDecodeError:
                            print(f"Warning: Invalid JSON response for {endpoint_path} [{method}]")
                            if endpoint_path not in results:
                                results[endpoint_path] = {}
                            results[endpoint_path][method] = {"error": "Failed to parse JSON from Gemini response"}

                    except (KeyError, IndexError):
                        print(f"Error extracting response from Gemini for {endpoint_path} [{method}]")
                        if endpoint_path not in results:
                            results[endpoint_path] = {}
                        results[endpoint_path][method] = {"error": "Failed to get proper response from Gemini"}
                else:
                    print(f"Skipping endpoint {endpoint_path} [{method}] with no code...")

        # Save the results to the output file with the desired format
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Successfully processed {processed} endpoint-method combinations and saved results to {output_file}")

    except Exception as e:
        print(f"Error processing endpoints: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    load_dotenv(override=True)
    # Check for command line arguments
    if len(sys.argv) >= 4:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        api_key = sys.argv[3]
        model = sys.argv[4] if len(sys.argv) >= 5 else "gemini-2.0-flash"
    else:
        # Default values if not provided as command line arguments
        input_file = "./flask_routes.json"
        output_file = "./mitm/json_schema/request_schemas.json"
        api_key = os.getenv("GEMINI_API_KEY","")
        model = "gemini-2.0-flash"

    # Process the endpoints
    process_flask_endpoints(input_file, output_file, api_key, model)