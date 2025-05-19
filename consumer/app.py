from flask import Flask, jsonify, request
import requests
import os
import traceback
from flasgger import Swagger
from flask_cors import CORS

app = Flask(__name__)

# Enable CORS for all routes with additional configuration
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Use environment variables for proxy and backend
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:5100')
PROXY_URL = os.getenv('PROXY_URL', 'http://mitm:8091')

# Configure Swagger with CORS in mind
swagger_config = {
    "swagger_version": "2.0",
    "headers": [
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
        ('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    ],
    "specs": [
        {
            "endpoint": 'swagger',
            "route": '/swagger.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger/"
}

swagger = Swagger(app, config=swagger_config)
proxies = {'http': PROXY_URL}

@app.route('/submit', methods=['POST'])
def handle_complex_json():
    """
    Handle complex JSON submission.
    ---
    post:
      summary: Accept and validate a complex JSON object
      description: >
        This endpoint accepts a JSON payload containing user information,
        preferences, history of actions, and optional settings.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - user
                - preferences
                - history
              properties:
                user:
                  type: object
                  required:
                    - id
                    - name
                  properties:
                    id:
                      type: integer
                      example: 123
                    name:
                      type: object
                      required:
                        - first
                        - last
                      properties:
                        first:
                          type: string
                          example: John
                        last:
                          type: string
                          example: Doe
                preferences:
                  type: object
                  required:
                    - notifications
                  properties:
                    notifications:
                      type: boolean
                      example: true
                history:
                  type: array
                  items:
                    type: object
                    required:
                      - timestamp
                      - action
                    properties:
                      timestamp:
                        type: string
                        format: date-time
                        example: "2023-10-26T10:00:00Z"
                      action:
                        type: string
                        example: login
                settings:
                  type: object
                  properties:
                    theme:
                      type: string
                      example: dark
      responses:
        200:
          description: JSON received and validated
        400:
          description: Validation error
        500:
          description: Internal server error
    """
    try:
        data = request.get_json(force=True)

        required_keys = ['user', 'preferences', 'history']
        for key in required_keys:
            if key not in data:
                return jsonify({"error": f"Missing key: '{key}'"}), 400

        user = data['user']
        if not isinstance(user.get('id'), int):
            return jsonify({"error": "User ID must be an integer"}), 400
        if not isinstance(user.get('name'), dict):
            return jsonify({"error": "User name must be a dictionary with 'first' and 'last'"}), 400

        name = user['name']
        if 'first' not in name or 'last' not in name:
            return jsonify({"error": "Missing 'first' or 'last' in user name"}), 400

        preferences = data['preferences']
        if 'notifications' not in preferences or not isinstance(preferences['notifications'], bool):
            return jsonify({"error": "'notifications' must be a boolean in preferences"}), 400

        history = data['history']
        if not isinstance(history, list):
            return jsonify({"error": "'history' must be a list"}), 400
        for idx, item in enumerate(history):
            if 'timestamp' not in item or 'action' not in item:
                return jsonify({"error": f"Missing 'timestamp' or 'action' in history item {idx}"}), 400

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

@app.route('/send_with_proxy', methods=['POST'])
def send_with_proxy():
    """
    Send data through the mitmproxy to the backend
    ---
    parameters:
      - name: data
        in: body
        required: true
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: object
              properties:
                first_name:
                  type: string
                second_name:
                  type: string
            message:
              type: string
            source:
              type: string
            age:
              type: integer
    responses:
      200:
        description: Response from backend through proxy
    """
    data = request.get_json()
    response = requests.post(f"{BACKEND_URL}/receive", proxies=proxies, json=data)
    return response.json()

@app.route('/send_direct', methods=['POST'])
def send_direct():
    """
    Send data directly to the backend without mitmproxy
    ---
    parameters:
      - name: data
        in: body
        required: false
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            message:
              type: string
            source:
              type: string
            age:
              type: integer
    responses:
      200:
        description: Direct response from backend
    """
    data = request.get_json()
    response = requests.post(f"{BACKEND_URL}/receive", json=data)
    return response.json()

invalid_api = {
    "id": 123,
    "nme": "Jasser",
    "messages": "Hello",
    "sourc": "consumer",
    "ae": 22
}

valid_api = {
    "id": 123,
    "name": "Jasser",
    "message": "Hello",
    "source": "consumer",
    "age": 22
}

@app.route('/valid')
def send():
    response = requests.post(f"{PROXY_URL}/receive", json=valid_api)
    return response.json()

@app.route('/invalid')
def valid():
    response = requests.post(f"{BACKEND_URL}/receive", json=invalid_api, proxies=proxies)
    return response.json()

@app.route('/invalid_proxy')
def invalid():
    response = requests.post(f"{BACKEND_URL}/receive", proxies=proxies, json=invalid_api)
    return response.json()

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
