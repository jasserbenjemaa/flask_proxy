from flask import Flask, jsonify
import requests
import os
import urllib3

# Disable SSL warnings since we're using verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Use environment variable for backend URL with fallback
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:5100')
PROXY_URL= os.getenv('PROXY_URL', 'http://mitm:8091')

@app.route('/')
def index():
    # Configure the proxy for both HTTP and HTTPS
    proxies = {
        'http':PROXY_URL,
    }

    try:
        # Make request through mitmproxy with timeout
        response = requests.get(
            f"{BACKEND_URL}/api/time",
            proxies=proxies,
        )
        response.raise_for_status()  # Raise exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Request failed',
            'message': str(e),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
