from flask import Flask, request, jsonify
import threading
import llm_module  # Import the module we created earlier

app = Flask(__name__)

@app.route('/api', methods=['POST'])
def generate():
    """Generate a response to a single prompt"""
    try:
        data = request.json

        # Extract parameters with defaults
        provider = data.get('provider', 'anthropic')
        model = data.get('model')
        prompt = data.get('prompt')
        system_message = data.get('system_message')
        temperature = float(data.get('temperature', 0.7))
        max_tokens = int(data.get('max_tokens', 1000))


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

        # Return response
        return jsonify({
            "response": result["content"],
            #"cost_info": result["cost_info"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['POST'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
