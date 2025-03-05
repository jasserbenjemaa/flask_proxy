from flask import Flask, request, jsonify
import traceback
import os
import llm_module  # Import the module we created earlier

app = Flask(__name__)

@app.route('/api', methods=['POST'])
def generate():
    """Generate a response to a single prompt"""
    try:

        data = request.get_json()
        backend_error = data["backend_error"]
        client_req = data["client_req"]

        prompt=f"this error {backend_error} caused by this api request from the client {client_req}"
        system_message = """your goal is to give me python function named 'fix_api'
        the function take dict and return corrected one to prevent the error i don't want any data lost
        don't add any thing or importing just the code without Docstring"""

        provider = "gemini"
        model = "gemini-2.0-flash-lite"
        temperature = 0.7
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
            system_message=system_message,
            #token_price=token_price
        )

        # Save costs asynchronously
        #threading.Thread(target=llm_module.save_costs).start()


        with open('./api_correction_scripts/client.py','w') as f:
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
