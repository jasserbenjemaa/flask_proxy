from flask import Flask
import requests
import os

app = Flask(__name__)

# Use environment variable for backend URL with fallback
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:5100')
PROXY_URL= os.getenv('PROXY_URL', 'http://mitm:8091')



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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
