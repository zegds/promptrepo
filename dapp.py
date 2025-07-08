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

def create_seed_data():
    """Create initial seed data with example folder and prompts"""
    now = int(time.time() * 1000)
    
    # Create example folder
    example_folder = {
        'id': str(now),
        'name': 'Example Prompts',
        'expanded': False,
        'order': 0,
        'parentId': None
    }
    
    # Create example prompts
    prompts = [
        {
            'id': str(now + 1),
            'name': 'Creative Writing Assistant',
            'text': 'You are a creative writing assistant. Help me brainstorm ideas, develop characters, and improve my storytelling. Please ask clarifying questions to better understand what kind of story I want to write.',
            'folderId': example_folder['id'],
            'order': 0,
            'versions': [{
                'id': f"{now + 1}-v1",
                'name': 'Creative Writing Assistant',
                'text': 'You are a creative writing assistant. Help me brainstorm ideas, develop characters, and improve my storytelling. Please ask clarifying questions to better understand what kind of story I want to write.',
                'timestamp': now + 1,
                'version': 1
            }],
            'currentVersion': 1,
            'usageCount': 0
        },
        {
            'id': str(now + 2),
            'name': 'Code Review Helper',
            'text': 'Please review the following code and provide feedback on:\n1. Code quality and best practices\n2. Potential bugs or issues\n3. Performance improvements\n4. Readability and maintainability\n\nCode to review:\n[PASTE CODE HERE]',
            'folderId': example_folder['id'],
            'order': 1,
            'versions': [{
                'id': f"{now + 2}-v1",
                'name': 'Code Review Helper',
                'text': 'Please review the following code and provide feedback on:\n1. Code quality and best practices\n2. Potential bugs or issues\n3. Performance improvements\n4. Readability and maintainability\n\nCode to review:\n[PASTE CODE HERE]',
                'timestamp': now + 2,
                'version': 1
            }],
            'currentVersion': 1,
            'usageCount': 0
        },
        {
            'id': str(now + 3),
            'name': 'Meeting Summary Generator',
            'text': 'Please create a concise meeting summary from the following notes. Include:\n- Key decisions made\n- Action items with owners\n- Important discussion points\n- Next steps\n\nMeeting notes:\n[PASTE NOTES HERE]',
            'folderId': example_folder['id'],
            'order': 2,
            'versions': [{
                'id': f"{now + 3}-v1",
                'name': 'Meeting Summary Generator',
                'text': 'Please create a concise meeting summary from the following notes. Include:\n- Key decisions made\n- Action items with owners\n- Important discussion points\n- Next steps\n\nMeeting notes:\n[PASTE NOTES HERE]',
                'timestamp': now + 3,
                'version': 1
            }],
            'currentVersion': 1,
            'usageCount': 0
        }
    ]
    
    return {
        'prompts': prompts,
        'folders': [example_folder]
    }

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
                        
                return data
        except json.JSONDecodeError:
            pass
    
    # If file doesn't exist or is corrupted, create seed data
    print("Creating new config.json with seed data...")
    seed_data = create_seed_data()
    save_data(seed_data)
    return seed_data

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
    
    # Get the highest order number for items in the same container
    folder_id = prompt_data.get('folderId')
    
    # Get all items in the same container
    container_folders = [f for f in data['folders'] if f.get('parentId') == folder_id]
    container_prompts = [p for p in data['prompts'] if p.get('folderId') == folder_id]
    all_items = container_folders + container_prompts
    max_order = max([item.get('order', 0) for item in all_items], default=-1)
    
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
    
    # Get the highest order number for items in the same container
    parent_id = folder_data.get('parentId')
    
    # Get all items in the same container
    container_folders = [f for f in data['folders'] if f.get('parentId') == parent_id]
    container_prompts = [p for p in data['prompts'] if p.get('folderId') == parent_id]
    all_items = container_folders + container_prompts
    max_order = max([item.get('order', 0) for item in all_items], default=-1)
    
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
    """Move an item (prompt or folder) to a new position"""
    try:
        data = load_data()
        move_data = request.json
        
        item_type = move_data.get('type')  # 'prompt' or 'folder'
        item_id = move_data.get('itemId')
        target_container = move_data.get('targetContainer')  # folder ID or null for root
        target_position = move_data.get('targetPosition')  # index in the target container
        
        print(f"Moving {item_type} {item_id} to container {target_container} at position {target_position}")
        
        # Find the item being moved
        moved_item = None
        if item_type == 'prompt':
            for p in data['prompts']:
                if p['id'] == item_id:
                    moved_item = p
                    break
        else:  # folder
            for f in data['folders']:
                if f['id'] == item_id:
                    moved_item = f
                    break
        
        if not moved_item:
            return jsonify({'error': f'{item_type.title()} not found'}), 404
        
        # For folders, check circular reference
        if item_type == 'folder':
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
        
        # Update the item's container
        if item_type == 'prompt':
            moved_item['folderId'] = target_container
        else:
            moved_item['parentId'] = target_container
        
        # Get all items in the target container
        container_folders = [f for f in data['folders'] if f.get('parentId') == target_container]
        container_prompts = [p for p in data['prompts'] if p.get('folderId') == target_container]
        
        # Create a combined list of all items in the container
        all_items = []
        for f in container_folders:
            all_items.append({'id': f['id'], 'type': 'folder', 'order': f.get('order', 0), 'item': f})
        for p in container_prompts:
            all_items.append({'id': p['id'], 'type': 'prompt', 'order': p.get('order', 0), 'item': p})
        
        # Sort by current order
        all_items.sort(key=lambda x: x['order'])
        
        # Remove the moved item from the list (it might already be in this container)
        all_items = [item for item in all_items if item['id'] != item_id]
        
        # Insert the moved item at the target position
        if target_position is None:
            target_position = len(all_items)
        
        target_position = max(0, min(target_position, len(all_items)))
        
        moved_item_entry = {
            'id': item_id, 
            'type': item_type, 
            'order': target_position, 
            'item': moved_item
        }
        all_items.insert(target_position, moved_item_entry)
        
        # Update order values for all items
        for i, item_entry in enumerate(all_items):
            item_entry['item']['order'] = i
        
        print(f"Reordered {len(all_items)} items in container {target_container}")
        
        save_data(data)
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error in move_item: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
