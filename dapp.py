from flask import Flask, jsonify, request, render_template
import os
import json
import time
from pathlib import Path

app = Flask(__name__)

DOCUMENTS_DIR = Path.home() / 'Documents' / 'PromptData'
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DOCUMENTS_DIR / 'config.json'

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
                
                # Ensure all folders have order field and parentId
                for i, folder in enumerate(data.get('folders', [])):
                    if 'order' not in folder:
                        folder['order'] = i
                    if 'parentId' not in folder:
                        folder['parentId'] = None
                    if 'expanded' not in folder:
                        folder['expanded'] = True
                
                # Sort folders by order
                data['folders'] = sorted(data.get('folders', []), key=lambda x: x.get('order', 0))
                
                return data
        except json.JSONDecodeError:
            pass
    return {'prompts': [], 'folders': []}

def save_data(data):
    """Save data to config.json"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_folder_hierarchy():
    """Get folders organized in hierarchy"""
    data = load_data()
    folders = data['folders']
    
    # Create a map for quick lookup
    folder_map = {f['id']: f for f in folders}
    
    # Add children array to each folder
    for folder in folders:
        folder['children'] = []
    
    # Build hierarchy
    root_folders = []
    for folder in folders:
        if folder['parentId'] and folder['parentId'] in folder_map:
            folder_map[folder['parentId']]['children'].append(folder)
        else:
            root_folders.append(folder)
    
    return root_folders

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
    
    # Get the highest order number for folders at the same level
    parent_id = folder_data.get('parentId')
    same_level_folders = [f for f in data['folders'] if f.get('parentId') == parent_id]
    max_order = max([f.get('order', 0) for f in same_level_folders], default=-1)
    
    new_folder = {
        'id': str(int(time.time() * 1000)),
        'name': folder_data['name'],
        'expanded': True,
        'order': max_order + 1,
        'parentId': parent_id
    }
    
    data['folders'].append(new_folder)
    save_data(data)
    return jsonify(new_folder)

@app.route('/api/folders/<folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    """Delete a folder (moves prompts and subfolders to parent)"""
    data = load_data()
    
    # Find the folder being deleted
    folder_to_delete = None
    for folder in data['folders']:
        if folder['id'] == folder_id:
            folder_to_delete = folder
            break
    
    if not folder_to_delete:
        return jsonify({'error': 'Folder not found'}), 404
    
    parent_id = folder_to_delete.get('parentId')
    
    # Move child folders to parent
    for folder in data['folders']:
        if folder.get('parentId') == folder_id:
            folder['parentId'] = parent_id
    
    # Move prompts to parent folder
    for prompt in data['prompts']:
        if prompt.get('folderId') == folder_id:
            prompt['folderId'] = parent_id
    
    # Remove folder
    data['folders'] = [f for f in data['folders'] if f['id'] != folder_id]
    
    save_data(data)
    return jsonify({'success': True})

@app.route('/api/folders/<folder_id>/move-up', methods=['POST'])
def move_folder_up(folder_id):
    """Move folder up in order"""
    data = load_data()
    
    # Find the folder
    folder = None
    for f in data['folders']:
        if f['id'] == folder_id:
            folder = f
            break
    
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404
    
    # Get siblings (folders with same parent)
    siblings = [f for f in data['folders'] if f.get('parentId') == folder.get('parentId')]
    siblings.sort(key=lambda x: x.get('order', 0))
    
    # Find current position
    current_index = next((i for i, f in enumerate(siblings) if f['id'] == folder_id), -1)
    
    if current_index > 0:
        # Swap orders with previous sibling
        prev_folder = siblings[current_index - 1]
        folder['order'], prev_folder['order'] = prev_folder['order'], folder['order']
        
        save_data(data)
        return jsonify({'success': True})
    
    return jsonify({'error': 'Cannot move up'}), 400

@app.route('/api/folders/<folder_id>/move-down', methods=['POST'])
def move_folder_down(folder_id):
    """Move folder down in order"""
    data = load_data()
    
    # Find the folder
    folder = None
    for f in data['folders']:
        if f['id'] == folder_id:
            folder = f
            break
    
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404
    
    # Get siblings (folders with same parent)
    siblings = [f for f in data['folders'] if f.get('parentId') == folder.get('parentId')]
    siblings.sort(key=lambda x: x.get('order', 0))
    
    # Find current position
    current_index = next((i for i, f in enumerate(siblings) if f['id'] == folder_id), -1)
    
    if current_index < len(siblings) - 1:
        # Swap orders with next sibling
        next_folder = siblings[current_index + 1]
        folder['order'], next_folder['order'] = next_folder['order'], folder['order']
        
        save_data(data)
        return jsonify({'success': True})
    
    return jsonify({'error': 'Cannot move down'}), 400

@app.route('/api/folders/<folder_id>/move', methods=['POST'])
def move_folder(folder_id):
    """Move folder to different parent"""
    data = load_data()
    new_parent_id = request.json.get('parentId')
    
    # Find the folder
    folder = None
    for f in data['folders']:
        if f['id'] == folder_id:
            folder = f
            break
    
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404
    
    # Check for circular reference
    def would_create_cycle(folder_id, target_parent_id):
        if target_parent_id is None:
            return False
        if target_parent_id == folder_id:
            return True
        
        for f in data['folders']:
            if f['id'] == target_parent_id:
                return would_create_cycle(folder_id, f.get('parentId'))
        return False
    
    if would_create_cycle(folder_id, new_parent_id):
        return jsonify({'error': 'Cannot create circular reference'}), 400
    
    # Update parent
    folder['parentId'] = new_parent_id
    
    # Update order to be last in new parent
    siblings = [f for f in data['folders'] if f.get('parentId') == new_parent_id and f['id'] != folder_id]
    max_order = max([f.get('order', 0) for f in siblings], default=-1)
    folder['order'] = max_order + 1
    
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
