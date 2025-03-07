from flask import Flask, jsonify, request
import requests
import os
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
              example: 123
            name:
              type: string
              example: "Jasser"
            message:
              type: string
              example: "Hello"
            source:
              type: string
              example: "consumer"
            age:
              type: integer
              example: 22
    responses:
      200:
        description: Response from backend through proxy
    """
    data = request.get_json()
    # Use the PROXY_URL to send data to the backend
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
        required: true
        schema:
          type: object
          properties:
            id:
              type: integer
              example: 123
            name:
              type: string
              example: "Jasser"
            message:
              type: string
              example: "Hello"
            source:
              type: string
              example: "consumer"
            age:
              type: integer
              example: 22
    responses:
      200:
        description: Direct response from backend
    """
    data = request.get_json()
    # Send directly to the backend without using a proxy
    response = requests.post(f"{BACKEND_URL}/receive", json=data)
    return response.json()


invalid_api = {
        "id":123,
        "nme": "Jasser",
        "messages": "Hello",
        "sourc": "consumer",
        "ae":22
    }

valid_api = {
        "id":123,
        "name": "Jasser",
        "message": "Hello",
        "source": "consumer",
        "age":22
    }
proxies = {
        'http':PROXY_URL,
    }

@app.route('/valid')
def send():
    response = requests.post(
        f"{PROXY_URL}/receive",
        json=valid_api
        )
    return response.json()



@app.route('/invalid')
def valid():

    response = requests.post(
        f"{BACKEND_URL}/receive",
        json=invalid_api
        )
    return response.json()

@app.route('/invalid_proxy')
def invalid():
    response = requests.post(
        f"{BACKEND_URL}/receive",
        proxies=proxies,
        json=invalid_api
        )
    return response.json()


# Add an explicit OPTIONS handler for preflight requests
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)