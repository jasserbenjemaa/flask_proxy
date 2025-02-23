from flask import Flask,request,jsonify
from interface_fun.gemini_interface_func import correct_api
app = Flask(__name__)

@app.route('/api',methods=['POST'])
def send_api_to_llm():
    data = request.get_json()
    invalid_api=data["invalid_api"]
    api_schema=data["api_schema"]
    return jsonify(correct_api(invalid_api,api_schema))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
