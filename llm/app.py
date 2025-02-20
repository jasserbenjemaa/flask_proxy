from flask import Flask, jsonify
from interface_fun.gemini_interface_func import correct_api
app = Flask(__name__)

@app.route('/api')
def get_time():
    return correct_api("api","api_schema")
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
