from flask import Flask, jsonify ,request
import datetime

app = Flask(__name__)

@app.route('/api/time')
def get_time():
    return jsonify({
        'time': datetime.datetime.utcnow().isoformat(),
        'message': 'Hello from Backend!',
        'source': 'backend-container'
    })
@app.route('/receive',methods=['POST'])
def receive_json():
    data = request.get_json()
    return jsonify({"received_data":data,"message":"Hello from Backend!","source":"backend-container"})
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100)
