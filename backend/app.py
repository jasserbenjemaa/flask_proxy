from flask import Flask, jsonify ,request,render_template
import traceback
import logging
from flask_cors import CORS
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.route('/receive',methods=['POST'])
def receive_json():
    try:
        data = request.get_json()
        return jsonify({"second_name":data['name']["second_name"],"name_first":data['name']["first_name"],"message":data["message"],"source":data["source"],"age":data["age"]})
    except Exception as e:
        error_trace = traceback.format_exc()
        return jsonify({"traceback":error_trace}), 400

@app.route('/add', methods=['POST'])
def handle_complex_json():
    try:
        data = request.get_json(force=True)

        # Validate presence of top-level keys
        required_keys = ['user', 'preferences', 'history']
        for key in required_keys:
            if key not in data:
                return jsonify({"error": f"Missing key: '{key}'"}), 400

        # Validate 'user' object
        user = data['user']
        if not isinstance(user.get('id'), int):
            return jsonify({"error": "User ID must be an integer"}), 400
        if not isinstance(user.get('name'), dict):
            return jsonify({"error": "User name must be a dictionary with 'first' and 'last'"}), 400

        # Validate name structure
        name = user['name']
        if 'first' not in name or 'last' not in name:
            return jsonify({"error": "Missing 'first' or 'last' in user name"}), 400

        # Validate preferences
        preferences = data['preferences']
        if 'notifications' not in preferences or not isinstance(preferences['notifications'], bool):
            return jsonify({"error": "'notifications' must be a boolean in preferences"}), 400

        # Validate history (list of past actions)
        history = data['history']
        if not isinstance(history, list):
            return jsonify({"error": "'history' must be a list"}), 400

        for idx, item in enumerate(history):
            if 'timestamp' not in item or 'action' not in item:
                return jsonify({"error": f"Missing 'timestamp' or 'action' in history item {idx}"}), 400

        # Optional section: settings
        settings = data.get('settings', {})
        theme = settings.get('theme', 'light')

        return jsonify({
            "message": "JSON received and validated",
            "user_id": user['id'],
            "user_name": f"{name['first']} {name['last']}",
            "notifications_enabled": preferences['notifications'],
            "history_count": len(history),
            "theme": theme
        })

    except Exception:
        return jsonify({"traceback": traceback.format_exc()}), 500


@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/submit', methods=['POST'])
def submit_form():
    logger.info("Received a POST request to /submit")
    try:
        data = request.form
        name = data["name"]
        email = data.get('email')
        message = data.get('message')
        

        logger.info(f"Received form submission - Name: {name}, Email: {email} message:{message}")

        # Process the form data here
        return jsonify({
            "status": "success",
            "message": "Form submitted successfully"
        }), 200
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.info(f"backend error: {error_trace}")
        logger.error(f"Error processing form: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "An error occurred while processing the form",
            "traceback":error_trace
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100)
