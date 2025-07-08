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
                for i, prompt in enumerate(data.get('prompts', [])):
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
                    if 'order' not in prompt:
                        prompt['order'] = i
                        
                # Ensure all folders have order field and parentId
                for i, folder in enumerate(data.get('folders', [])):
                    if 'order' not in folder:
                        folder['order'] = i
                    if 'parentId' not in folder:
                        folder['parentId'] = None
                    # Don't override existing expanded state, but default to False
                    if 'expanded' not in folder:
                        folder['expanded'] = False
                        
                # Sort folders and prompts by order
                data['folders'] = sorted(data.get('folders', []), key=lambda x: x.get('order', 0))
                data['prompts'] = sorted(data.get('prompts', []), key=lambda x: x.get('order', 0))
                        
                return data
        except json.JSONDecodeError:
            pass
    return {'prompts': [], 'folders': []}

def save_data(data):
    """Save data to config.json"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def reorder_items_in_container(items, moved_item_id, new_position):
    """Reorder items within a container, maintaining proper order values"""
    # Remove the moved item
    moved_item = None
    filtered_items = []
    for item in items:
        if item['id'] == moved_item_id:
            moved_item = item
        else:
            filtered_items.append(item)
    
    if not moved_item:
        return items
    
    # Clamp position to valid range
    new_position = max(0, min(new_position, len(filtered_items)))
    
    # Insert at new position
    filtered_items.insert(new_position, moved_item)
    
    # Update order values
    for i, item in enumerate(filtered_items):
        item['order'] = i
    
    return filtered_items

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
    
    # Get the highest order number for prompts in the same folder
    folder_id = prompt_data.get('folderId')
    siblings = [p for p in data['prompts'] if p.get('folderId') == folder_id]
    max_order = max([p.get('order', 0) for p in siblings], default=-1)
    
    now = int(time.time() * 1000)
    new_prompt = {
        'id': str(now),
        'name': prompt_data['name'],
        'text': prompt_data['text'],
        'folderId': folder_id,
        'order': max_order + 1,
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
    
    # Get the highest order number for the same parent level
    parent_id = folder_data.get('parentId')
    siblings = [f for f in data['folders'] if f.get('parentId') == parent_id]
    max_order = max([f.get('order', 0) for f in siblings], default=-1)
    
    new_folder = {
        'id': str(int(time.time() * 1000)),
        'name': folder_data['name'],
        'expanded': False,  # Always default to closed
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

@app.route('/api/items/move', methods=['POST'])
def move_item():
    """Move an item (prompt or folder) to a new position with intelligent positioning"""
    try:
        data = load_data()
        move_data = request.json
        
        item_type = move_data.get('type')  # 'prompt' or 'folder'
        item_id = move_data.get('itemId')
        target_container = move_data.get('targetContainer')  # folder ID or null for root
        target_position = move_data.get('targetPosition')  # index in the target container
        
        print(f"Moving {item_type} {item_id} to container {target_container} at position {target_position}")
        
        if item_type == 'prompt':
            # Find the prompt
            prompt = None
            for p in data['prompts']:
                if p['id'] == item_id:
                    prompt = p
                    break
            
            if not prompt:
                return jsonify({'error': 'Prompt not found'}), 404
            
            # Update folder
            prompt['folderId'] = target_container
            
            # Get all prompts in the target container
            container_prompts = [p for p in data['prompts'] if p.get('folderId') == target_container]
            
            # If no position specified, put at end
            if target_position is None:
                target_position = len(container_prompts) - 1  # -1 because we're already in the list
            
            # Clamp position to valid range
            target_position = max(0, min(target_position, len(container_prompts) - 1))
            
            # Reorder prompts in the target container
            reordered_prompts = reorder_items_in_container(container_prompts, item_id, target_position)
            
            # Update the main prompts list
            for i, p in enumerate(data['prompts']):
                if p.get('folderId') == target_container:
                    for reordered in reordered_prompts:
                        if p['id'] == reordered['id']:
                            data['prompts'][i] = reordered
                            break
        
        elif item_type == 'folder':
            # Find the folder
            folder = None
            for f in data['folders']:
                if f['id'] == item_id:
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
            
            if would_create_cycle(item_id, target_container):
                return jsonify({'error': 'Cannot create circular reference'}), 400
            
            # Update parent
            folder['parentId'] = target_container
            
            # Get all folders in the target container
            container_folders = [f for f in data['folders'] if f.get('parentId') == target_container]
            
            # If no position specified, put at end
            if target_position is None:
                target_position = len(container_folders) - 1  # -1 because we're already in the list
            
            # Clamp position to valid range
            target_position = max(0, min(target_position, len(container_folders) - 1))
            
            # Reorder folders in the target container
            reordered_folders = reorder_items_in_container(container_folders, item_id, target_position)
            
            # Update the main folders list
            for i, f in enumerate(data['folders']):
                if f.get('parentId') == target_container:
                    for reordered in reordered_folders:
                        if f['id'] == reordered['id']:
                            data['folders'][i] = reordered
                            break
        
        save_data(data)
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error in move_item: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
