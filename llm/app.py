from flask import Flask, request, jsonify
import traceback
import llm_module  # Import the module we created earlier

app = Flask(__name__)

@app.route('/api', methods=['POST'])
def generate():
    """Generate a response to a single prompt"""
    try:
        data = request.get_json()
        backend_errors = data["backend_errors"]
        client_req = data["client_req"]
        file_path = data["file_path"]
        content_type = request.headers.get("Content-Type", "")

        prompt_json = f"""this errors {backend_errors} was caused by this API request from the client: {client_req}.
        Generate a complete Python script that:
        - Takes a JSON dictionary as an argument from the command line.
        - Processes the input and corrects it to prevent the error.
        - Prints the corrected dictionary as a JSON string.
        - I don't want None values the data exist but the key may have a slightly diffrent name.
        - Does not lose any data.
        Your output should be a valid Python script. Do not include explanations, comments, or import statements—just the raw script."""

        prompt_form = f"""This error {backend_errors} was caused by a multipart/form-data API request from the client: {client_req}.
        Generate a complete Python script that:
        - Don't import any library that requires installation use regular experation.
        - Takes the raw multipart form data as input from the command line.
        - Processes the input and corrects it to prevent the error.
        - Ensures all form fields and file content are properly formatted.
        - Outputs the corrected multipart form data.
        - Handles any encoding issues common with multipart form data.
        Your output should be a valid Python script. Do not include explanations, comments, or import statements—just the raw script."""

        prompt_app_form = f"""This error {backend_errors} was caused by an application/x-www-form-urlencoded API request from the client: {client_req}.
        Generate a complete Python script that:
        - Takes the raw URL-encoded form data as input from the command line.
        - Correctly formats key-value pairs to fix any naming or structure issues.
        - Ensures proper URL encoding of special characters in form values.
        - Outputs the corrected URL-encoded form data.
        - Preserves all original data - the data exists but parameter names may have slightly different formats.
        - Handles common URL encoding/decoding issues.
        Your output should be a valid Python script. Do not include explanations, comments, or import statements—just the raw script."""

        match content_type:
            case "application/json":
                prompt = prompt_json
            case "multipart/form-data":
                prompt = prompt_form
            case "application/x-www-form-urlencoded":
                prompt = prompt_app_form
            case _:
                return jsonify({"error": "Unsupported content type"}), 400

        provider = "gemini"
        model = "gemini-2.0-flash"
        temperature =1
        max_tokens = 8000


        # Validate required parameters
        if not prompt:
            return jsonify({"error": "prompt is required"}), 400

        # Create a new LLM instance
        llm, token_price = llm_module.create_llm_instance(
            provider=provider,
            model_name=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        if not llm:
            return jsonify({"error": "Failed to initialize LLM"}), 500


        # Send prompt to LLM
        result = llm_module.send_prompt(
            llm=llm,
            prompt=prompt,
            system_message="",
            #token_price=token_price
        )

        # Save costs asynchronously
        #threading.Thread(target=llm_module.save_costs).start()


        with open(f'./{file_path}','w') as f:
            from markdown_to_text import markdown_to_text
            llm_formated_result= markdown_to_text(result["content"])
            f.write(llm_formated_result)

        # Return response
        return jsonify({
            "response":result["content"],
            #"cost_info": result["cost_info"]
        })

    except Exception as e:
        error_trace = traceback.format_exc()
        return jsonify({"traceback":error_trace}), 500

@app.route('/health', methods=['POST'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
