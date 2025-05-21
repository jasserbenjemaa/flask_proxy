from Graph.graph import graph_init
from dotenv import load_dotenv

load_dotenv()

from dotenv import dotenv_values
code="""@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')

    if not name or not email:
        return jsonify({'error': 'Name and email are required'}), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO users (name, email) VALUES (%s, %s);',
                    (name, email)
                )
                conn.commit()
        return jsonify({'message': 'User added successfully'}), 201
    except psycopg2.IntegrityError:
        return jsonify({'error': 'Email already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500"""
# This returns a dict of only the .env file variables
dotenv_vars = dotenv_values(".env")

print(dotenv_vars)

def run_graph():
    graph_app=graph_init()
    print(graph_app.get_graph().draw_mermaid())
run_graph()
