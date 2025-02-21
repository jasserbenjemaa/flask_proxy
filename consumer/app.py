from flask import Flask
import requests
import os

app = Flask(__name__)

# Use environment variable for backend URL with fallback
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:5100')
PROXY_URL= os.getenv('PROXY_URL', 'http://mitm:8091')
proxies = {
        'http':PROXY_URL,
    }


@app.route('/')
def send_json():
    data = {'name':'Jasser', 'age': 21,'message':'req from the consumer'}
    response = requests.post(
        f"{BACKEND_URL}/receive",
        proxies=proxies,
        json=data
        )
    return response.json()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
