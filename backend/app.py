from flask import Flask, jsonify ,request,render_template
import traceback
import logging
from flask_cors import CORS
from supabase import create_client, Client
import os
from datetime import datetime
import uuid
import time
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


app = Flask(__name__)

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'your-supabase-url')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'your-supabase-anon-key')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Table name in Supabase
USERS_TABLE = 'users'

# Helper function to handle Supabase responses
def handle_supabase_response(response):
    if hasattr(response, 'data') and response.data is not None:
        return response.data
    else:
        # Handle error case
        error_msg = getattr(response, 'error', 'Unknown error occurred')
        raise Exception(str(error_msg))

# CREATE - Add a new user
@app.route('/users', methods=['POST'])
def create_user():
    time.sleep(4)
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'email' not in data:
            return jsonify({'error': 'Name and email are required'}), 400
        
        # Prepare user data
        user_data = {
            'id': str(uuid.uuid4()),
            'name': data['name'],
            'email': data['email'],
            'age': data.get('age'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Insert into Supabase
        response = supabase.table(USERS_TABLE).insert(user_data).execute()
        result = handle_supabase_response(response)
        
        return jsonify(result[0] if result else user_data), 201
    
    except Exception as e:
        error_msg = str(e)
        # Handle unique constraint violation (duplicate email)
        if 'duplicate key value' in error_msg or 'unique constraint' in error_msg:
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': error_msg}), 500

# READ - Get all users
@app.route('/users', methods=['GET'])
def get_all_users():
    try:
        # Optional query parameters for pagination and filtering
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = supabase.table(USERS_TABLE).select("*")
        
        # Add pagination
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        # Execute query
        response = query.execute()
        result = handle_supabase_response(response)
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get a specific user by ID
@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
        response = supabase.table(USERS_TABLE).select("*").eq('id', user_id).execute()
        result = handle_supabase_response(response)
        
        if not result:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(result[0]), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Search users by email
@app.route('/users/search', methods=['GET'])
def search_users():
    try:
        email = request.args.get('email')
        name = request.args.get('name')
        
        if not email and not name:
            return jsonify({'error': 'Email or name parameter required'}), 400
        
        query = supabase.table(USERS_TABLE).select("*")
        
        if email:
            query = query.ilike('email', f'%{email}%')
        if name:
            query = query.ilike('name', f'%{name}%')
        
        response = query.execute()
        result = handle_supabase_response(response)
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# UPDATE - Update a user (PUT)
@app.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Check if user exists
        check_response = supabase.table(USERS_TABLE).select("*").eq('id', user_id).execute()
        check_result = handle_supabase_response(check_response)
        
        if not check_result:
            return jsonify({'error': 'User not found'}), 404
        
        # Prepare update data
        update_data = {
            'updated_at': datetime.now().isoformat()
        }
        
        # Update provided fields
        if 'name' in data:
            update_data['name'] = data['name']
        if 'email' in data:
            update_data['email'] = data['email']
        if 'age' in data:
            update_data['age'] = data['age']
        
        # Update in Supabase
        response = supabase.table(USERS_TABLE).update(update_data).eq('id', user_id).execute()
        result = handle_supabase_response(response)
        
        if not result:
            return jsonify({'error': 'Update failed'}), 500
        
        return jsonify(result[0]), 200
    
    except Exception as e:
        error_msg = str(e)
        if 'duplicate key value' in error_msg or 'unique constraint' in error_msg:
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': error_msg}), 500

# UPDATE - Partial update (PATCH)
@app.route('/users/<user_id>', methods=['PATCH'])
def patch_user(user_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Check if user exists
        check_response = supabase.table(USERS_TABLE).select("*").eq('id', user_id).execute()
        check_result = handle_supabase_response(check_response)
        
        if not check_result:
            return jsonify({'error': 'User not found'}), 404
        
        # Prepare update data with only provided fields
        update_data = {'updated_at': datetime.now().isoformat()}
        
        for field in ['name', 'email', 'age']:
            if field in data:
                update_data[field] = data[field]
        
        # Update in Supabase
        response = supabase.table(USERS_TABLE).update(update_data).eq('id', user_id).execute()
        result = handle_supabase_response(response)
        
        if not result:
            return jsonify({'error': 'Update failed'}), 500
        
        return jsonify(result[0]), 200
    
    except Exception as e:
        error_msg = str(e)
        if 'duplicate key value' in error_msg or 'unique constraint' in error_msg:
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': error_msg}), 500

# DELETE - Delete a user
@app.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    time.sleep(4)
    try:
        # Get user before deletion
        check_response = supabase.table(USERS_TABLE).select("*").eq('id', user_id).execute()
        check_result = handle_supabase_response(check_response)
        
        if not check_result:
            return jsonify({'error': 'User not found'}), 404
        
        deleted_user = check_result[0]
        
        # Delete from Supabase
        response = supabase.table(USERS_TABLE).delete().eq('id', user_id).execute()
        handle_supabase_response(response)
        
        return jsonify({
            'message': 'User deleted successfully',
            'deleted_user': deleted_user
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    try:
        # Test connection by counting users
        response = supabase.table(USERS_TABLE).select("*", count="exact").execute()
        count = response.count if hasattr(response, 'count') else 0
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'total_users': count,
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

# Bulk operations
@app.route('/users/bulk', methods=['POST'])
def create_bulk_users():
    try:
        data = request.get_json()
        
        if not data or 'users' not in data or not isinstance(data['users'], list):
            return jsonify({'error': 'Users array is required'}), 400
        
        users_data = []
        for user in data['users']:
            if 'name' not in user or 'email' not in user:
                return jsonify({'error': 'Each user must have name and email'}), 400
            
            user_data = {
                'id': str(uuid.uuid4()),
                'name': user['name'],
                'email': user['email'],
                'age': user.get('age'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            users_data.append(user_data)
        
        # Insert bulk data
        response = supabase.table(USERS_TABLE).insert(users_data).execute()
        result = handle_supabase_response(response)
        
        return jsonify({
            'message': f'{len(result)} users created successfully',
            'users': result
        }), 201
    
    except Exception as e:
        error_msg = str(e)
        if 'duplicate key value' in error_msg or 'unique constraint' in error_msg:
            return jsonify({'error': 'One or more emails already exist'}), 409
        return jsonify({'error': error_msg}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Check environment variables
    if SUPABASE_URL == 'your-supabase-url' or SUPABASE_KEY == 'your-supabase-anon-key':
        print("⚠️  Warning: Please set SUPABASE_URL and SUPABASE_KEY environment variables")
        print("Example:")
        print("export SUPABASE_URL='https://your-project.supabase.co'")
        print("export SUPABASE_KEY='your-anon-key'")
    else:
        print("✅ Supabase configuration loaded")
        print(f"🔗 Supabase URL: {SUPABASE_URL}")
    
    print("🚀 Starting Flask app on http://0.0.0.0:5100")
    app.run( host='0.0.0.0', port=5100)
