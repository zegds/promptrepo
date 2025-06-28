from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)
CONFIG_PATH = "config.json"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'w') as f:
            json.dump({"folders": {}}, f)
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_config', methods=['GET'])
def get_config():
    return jsonify(load_config())

@app.route('/save_config', methods=['POST'])
def save_config_route():
    data = request.json
    save_config(data)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
