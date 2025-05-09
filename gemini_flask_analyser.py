import requests
import json
import os
from dotenv import load_dotenv
import sys
from typing import List, Dict, Any

def send_code_to_gemini(code_snippet: str, api_key: str, endpoint_path: str = "/",
                        methods: List[str] = [], model: str = "gemini-2.0-flash") -> Dict[str, Any]:
    """
    Send a flask code snippet to Gemini and get sample JSON payload that correctly satisfies
    the structure expected by this endpoint.

    Args:
        code_snippet: The code snippet to send to Gemini
        api_key: Your Gemini API key
        endpoint_path: The API endpoint path (for context)
        methods: List of HTTP methods for this endpoint
        model: The Gemini model to use (default: "gemini-2.0-flash")

    Returns:
        The response from Gemini
    """
    base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    url = f"{base_url}?key={api_key}"

    # Include endpoint path and methods in the prompt if available
    context = ""
    if endpoint_path:
        context += f"API Path: {endpoint_path}\n"
    if methods:
        context += f"HTTP Methods: {', '.join(methods)}\n"

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

        total_endpoints = len(flask_routes.keys())
        processed = 0

        for endpoint_path, endpoint_data in flask_routes.items():
            processed += 1
            print(f"Processing endpoint {processed}/{total_endpoints}: {endpoint_path}...")

            # Skip endpoints that don't accept POST/PUT/PATCH methods (typically don't need JSON payload)
            methods = endpoint_data.get("methods", [])
            write_methods = ["POST", "PUT", "PATCH"]
            if not any(method in write_methods for method in methods):
                print(f"Skipping {endpoint_path} as it doesn't use POST/PUT/PATCH methods...")
                continue

            if "code" in endpoint_data and endpoint_data["code"]:
                # Send the code to Gemini
                gemini_response = send_code_to_gemini(
                    endpoint_data["code"],
                    api_key,
                    endpoint_path=endpoint_path,
                    methods=methods,
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
                        # Add the result to our dictionary with endpoint path as key
                        results[endpoint_path] = json_payload
                    except json.JSONDecodeError:
                        print(f"Warning: Invalid JSON response for {endpoint_path}")
                        results[endpoint_path] = {"error": "Failed to parse JSON from Gemini response"}

                except (KeyError, IndexError):
                    print(f"Error extracting response from Gemini for {endpoint_path}")
                    results[endpoint_path] = {"error": "Failed to get proper response from Gemini"}
            else:
                print(f"Skipping endpoint {endpoint_path} with no code...")

        # Save the results to the output file with the desired format
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Successfully processed endpoints and saved results to {output_file}")

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
        api_key = os.getenv("GEMINI_API_KEY")
        model = "gemini-2.0-flash"

    # Process the endpoints
    process_flask_endpoints(input_file, output_file, api_key, model)