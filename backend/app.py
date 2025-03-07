from flask import Flask, jsonify ,request
import traceback
app = Flask(__name__)


@app.route('/receive',methods=['POST'])
def receive_json():
    try:
        data = request.get_json()
        return jsonify({"name":data['name'],"msg":data["message"],"source":data["source"],"age":data["age"]})
    except Exception as e:
        error_trace = traceback.format_exc()
        return jsonify({"traceback":error_trace}), 400



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100)
