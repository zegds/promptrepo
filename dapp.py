from flask import Flask, jsonify, request, render_template
import os
import json
import time

app = Flask(__name__)

DATA_FILE = 'config.json'
COOLDOWN_MINUTES = 3


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                data = json.load(f)
                for prompt in data.get('prompts', []):
                    if 'versions' not in prompt:
                        now = int(time.time() * 1000)
                        prompt['versions'] = [{
                            'id': f"{now}-v1",
                            'name': prompt['name'],
                            'text': prompt['text'],
                            'timestamp': now,
                            'version': 1
                        }]
                        prompt['currentVersion'] = 1
                    if 'usageCount' not in prompt:
                        prompt['usageCount'] = 0
                return data
            except json.JSONDecodeError:
                pass
    return {'prompts': [], 'folders': []}


def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify(load_data())


@app.route('/api/prompts', methods=['POST'])
def add_prompt():
    data = load_data()
    payload = request.json
    now = int(time.time() * 1000)
    new_prompt = {
        'id': str(now),
        'name': payload['name'],
        'text': payload['text'],
        'folderId': payload.get('folderId'),
        'versions': [{
            'id': f"{now}-v1",
            'name': payload['name'],
            'text': payload['text'],
            'timestamp': now,
            'version': 1
        }],
        'currentVersion': 1,
        'usageCount': 0
    }
    data['prompts'].append(new_prompt)
    save_data(data)
    return jsonify(new_prompt)


@app.route('/api/prompts/<prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    data = load_data()
    payload = request.json
    now = int(time.time() * 1000)
    for prompt in data['prompts']:
        if prompt['id'] == prompt_id:
            version_num = prompt['currentVersion'] + 1
            version_entry = {
                'id': f"{now}-v{version_num}",
                'name': payload.get('name', prompt['name']),
                'text': payload.get('text', prompt['text']),
                'timestamp': now,
                'version': version_num
            }
            prompt['name'] = version_entry['name']
            prompt['text'] = version_entry['text']
            prompt['versions'].append(version_entry)
            prompt['currentVersion'] = version_num
            break
    save_data(data)
    return jsonify({'success': True})


@app.route('/api/prompts/<prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    data = load_data()
    data['prompts'] = [p for p in data['prompts'] if p['id'] != prompt_id]
    save_data(data)
    return jsonify({'success': True})


@app.route('/api/prompts/<prompt_id>/copy', methods=['POST'])
def copy_prompt(prompt_id):
    data = load_data()
    now = int(time.time() * 1000)
    cooldown_ms = COOLDOWN_MINUTES * 60 * 1000
    for prompt in data['prompts']:
        if prompt['id'] == prompt_id:
            last_copied = prompt.get('lastCopiedAt', 0)
            if now - last_copied >= cooldown_ms:
                prompt['usageCount'] = prompt.get('usageCount', 0) + 1
                prompt['lastCopiedAt'] = now
            break
    save_data(data)
    return jsonify({'success': True})


@app.route('/api/prompts/<prompt_id>/restore/<version_id>', methods=['POST'])
def restore_prompt_version(prompt_id, version_id):
    data = load_data()
    for prompt in data['prompts']:
        if prompt['id'] == prompt_id:
            for version in prompt['versions']:
                if version['id'] == version_id:
                    prompt['name'] = version['name']
                    prompt['text'] = version['text']
                    break
            break
    save_data(data)
    return jsonify({'success': True})


@app.route('/api/prompts/<prompt_id>/move', methods=['POST'])
def move_prompt(prompt_id):
    data = load_data()
    folder_id = request.json.get('folderId')
    for prompt in data['prompts']:
        if prompt['id'] == prompt_id:
            prompt['folderId'] = folder_id
            break
    save_data(data)
    return jsonify({'success': True})


@app.route('/api/folders', methods=['POST'])
def add_folder():
    data = load_data()
    payload = request.json
    folder = {
        'id': str(int(time.time() * 1000)),
        'name': payload['name'],
        'expanded': True
    }
    data['folders'].append(folder)
    save_data(data)
    return jsonify(folder)


@app.route('/api/folders/<folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    data = load_data()
    data['folders'] = [f for f in data['folders'] if f['id'] != folder_id]
    for prompt in data['prompts']:
        if prompt.get('folderId') == folder_id:
            prompt['folderId'] = None
    save_data(data)
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True)
