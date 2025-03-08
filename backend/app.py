from flask import Flask, jsonify ,request,render_template
import traceback
import logging
from flask_cors import CORS
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.route('/receive',methods=['POST'])
def receive_json():
    try:
        data = request.get_json()
        return jsonify({"name":data['name'],"message":data["message"],"source":data["source"],"age":data["age"]})
    except Exception as e:
        error_trace = traceback.format_exc()
        return jsonify({"traceback":error_trace}), 400

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/submit', methods=['POST'])
def submit_form():
    logger.info("Received a POST request to /submit")
    try:
        data = request.form
        name = data["name"]
        email = data.get('email')
        message = data.get('message')

        logger.info(f"Received form submission - Name: {name}, Email: {email}")

        # Process the form data here
        return jsonify({
            "status": "success",
            "message": "Form submitted successfully"
        }), 200
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.info(f"backend error: {error_trace}")
        logger.error(f"Error processing form: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "An error occurred while processing the form",
            "traceback":error_trace
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100)
