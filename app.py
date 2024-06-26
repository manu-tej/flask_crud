
from flask import Flask, request, jsonify, send_from_directory, Response
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from elasticsearch import Elasticsearch

# Initialize Elasticsearch client with hosts parameter
es = Elasticsearch(hosts=["https://localhost:9200"], ca_certs="/Users/manuarrojwala/http_ca.crt", basic_auth=("elastic", "8TifduA1pgGizu-rKMO="))

app = Flask(__name__, static_folder='static', static_url_path='')

# Database connection
conn = psycopg2.connect(
    dbname="crud_db",
    user="postgres",
    password="",
    host="localhost"
)
cursor = conn.cursor(cursor_factory=RealDictCursor)

@app.route('/')
def index():
    print("Serving index.html at root")
    return send_from_directory('static', 'index.html')

# Index data
def index_data():
    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    for item in items:
        es.index(index='items', id=item['id'], body=item)

index_data()

# Create an item
@app.route('/items', methods=['POST'])
def create_item():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    cursor.execute('INSERT INTO items (name, description) VALUES (%s, %s) RETURNING *;', (name, description))
    new_item = cursor.fetchone()
    conn.commit()
    es.index(index='items', id=new_item['id'], body=new_item)
    return jsonify(new_item), 201

# Read all items
@app.route('/items', methods=['GET'])
def get_items():
    print('Fetching items')
    try:
        print("Executing SELECT query...")
        cursor.execute('SELECT * FROM items;')
        items = cursor.fetchall()
        print(f"Fetched items: {items}")
        return jsonify(items)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

# Update an item
@app.route('/items/<int:id>', methods=['PUT'])
def update_item(id):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    cursor.execute('UPDATE items SET name = %s, description = %s WHERE id = %s RETURNING *;', (name, description, id))
    updated_item = cursor.fetchone()
    conn.commit()
    es.index(index='items', id=updated_item['id'], body=updated_item)
    return jsonify(updated_item)

# Delete an item
@app.route('/items/<int:id>', methods=['DELETE'])
def delete_item(id):
    cursor.execute('DELETE FROM items WHERE id = %s RETURNING *;', (id,))
    deleted_item = cursor.fetchone()
    conn.commit()
    es.delete(index='items', id=id)
    return jsonify(deleted_item)

@app.route('/interface')
def serve_interface():
    print("Serving index.html at /interface")
    return send_from_directory('static', 'index.html')

@app.route('/search', methods=['GET'])
def search_items():
    query = request.args.get('query', '')
    search_body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["name", "description"],
                "fuzziness": "AUTO"
            }
        }
    }
    results = es.search(index='items', body=search_body)
    items = [hit['_source'] for hit in results['hits']['hits']]
    return jsonify(items)

@app.route('/suggestions', methods=['GET'])
def get_suggestions():
    query = request.args.get('query', '')
    print(f"Fetching suggestions for query: {query}")
    sql_query = "SELECT name, description FROM items WHERE name LIKE %s OR description LIKE %s LIMIT 10"
    params = (f'%{query}%', f'%{query}%')
    print(f"Executing SQL query: {sql_query} with params: {params}")
    cursor.execute(sql_query, params)
    suggestions = cursor.fetchall()
    print(f"Suggestions fetched: {suggestions}")
    response = json.dumps(suggestions)
    print(f"Returning response: {response}")
    return Response(response, content_type='application/json')

@app.route('/routes')
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint}: {methods} {rule}")
        output.append(line)
    return '<br>'.join(sorted(output))

if __name__ == '__main__':
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint}: {methods} {rule}")
        output.append(line)
    print('\n'.join(sorted(output)))
    app.run(debug=True)
