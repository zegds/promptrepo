from flask import Flask, render_template, request, jsonify
import json
import os
import time
from datetime import datetime

app = Flask(__name__)

# Configuration
DATA_FILE = 'config.json'
COOLDOWN_MINUTES = 3

def load_data():
    """Load data from config.json"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                # Ensure all prompts have required fields
                for prompt in data.get('prompts', []):
                    if 'versions' not in prompt:
                        prompt['versions'] = [{
                            'id': f"{int(time.time())}-v1",
                            'name': prompt['name'],
                            'text': prompt['text'],
                            'timestamp': int(time.time() * 1000),
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
    """Save data to config.json"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get all prompts and folders"""
    return jsonify(load_data())

@app.route('/api/prompts', methods=['POST'])
def add_prompt():
    """Add a new prompt"""
    data = load_data()
    prompt_data = request.json
    
    now = int(time.time() * 1000)
    new_prompt = {
        'id': str(now),
        'name': prompt_data['name'],
        'text': prompt_data['text'],
        'folderId': prompt_data.get('folderId'),
        'versions': [{
            'id': f"{now}-v1",
            'name': prompt_data['name'],
            'text': prompt_data['text'],
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
    """Update a prompt (creates new version)"""
    data = load_data()
    updates = request.json
    
    for prompt in data['prompts']:
        if prompt['id'] == prompt_id:
            new_version = prompt['currentVersion'] + 1
            now = int(time.time() * 1000)
            
            new_version_entry = {
                'id': f"{now}-v{new_version}",
                'name': updates.get('name', prompt['name']),
                'text': updates.get('text', prompt['text']),
                'timestamp': now,
                'version': new_version
            }
            
            prompt['name'] = updates.get('name', prompt['name'])
            prompt['text'] = updates.get('text', prompt['text'])
            prompt['versions'].append(new_version_entry)
            prompt['currentVersion'] = new_version
            break
    
    save_data(data)
    return jsonify({'success': True})

@app.route('/api/prompts/<prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete a prompt"""
    data = load_data()
    data['prompts'] = [p for p in data['prompts'] if p['id'] != prompt_id]
    save_data(data)
    return jsonify({'success': True})

@app.route('/api/prompts/<prompt_id>/copy', methods=['POST'])
def copy_prompt(prompt_id):
    """Track prompt copy with cooldown"""
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
def restore_version(prompt_id, version_id):
    """Restore a prompt to a previous version"""
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

@app.route('/api/folders', methods=['POST'])
def add_folder():
    """Add a new folder"""
    data = load_data()
    folder_data = request.json
    
    new_folder = {
        'id': str(int(time.time() * 1000)),
        'name': folder_data['name'],
        'expanded': True
    }
    
    data['folders'].append(new_folder)
    save_data(data)
    return jsonify(new_folder)

@app.route('/api/folders/<folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    """Delete a folder (moves prompts to root)"""
    data = load_data()
    
    # Remove folder
    data['folders'] = [f for f in data['folders'] if f['id'] != folder_id]
    
    # Move prompts to root
    for prompt in data['prompts']:
        if prompt.get('folderId') == folder_id:
            prompt['folderId'] = None
    
    save_data(data)
    return jsonify({'success': True})

@app.route('/api/prompts/<prompt_id>/move', methods=['POST'])
def move_prompt(prompt_id):
    """Move prompt to folder"""
    data = load_data()
    folder_id = request.json.get('folderId')
    
    for prompt in data['prompts']:
        if prompt['id'] == prompt_id:
            prompt['folderId'] = folder_id
            break
    
    save_data(data)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)
