from flask import Flask, jsonify
import datetime

app = Flask(__name__)

@app.route('/api/time')
def get_time():
    return jsonify({
        'time': datetime.datetime.utcnow().isoformat(),
        'message': 'Hello from Backend!',
        'source': 'backend-container'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100)
