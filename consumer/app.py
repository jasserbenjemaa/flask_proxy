from flask import Flask
import requests
import os

app = Flask(__name__)

# Use environment variable for backend URL with fallback
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:5100')
PROXY_URL= os.getenv('PROXY_URL', 'http://mitm:8091')

valid_api={
    "id": 123,
    "name": "Jasser",
    "message": "Request processed successfully",
    "source": "API Gateway"
}

invalid_api = {
    "received data from the consumer": "Invalid format",
    "message": 200,
    "source": {"name":"jasser"}
}


proxies = {
        'http':PROXY_URL,
    }

@app.route('/invalid')
def send():
    response = requests.post(
        f"{PROXY_URL}/receive",
        json=invalid_api
        )
    return response.json()



@app.route('/valid')
def send_json():
    response = requests.post(
        f"{BACKEND_URL}/receive",
        proxies=proxies,
        json=valid_api
        )
    return response.json()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
