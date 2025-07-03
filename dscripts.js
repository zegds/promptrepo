// Global state
let data = { prompts: [], folders: [] };
let selectedPrompt = null;
let selectedFolder = null;
let searchQuery = '';
let activeTab = 'repository';
let draggedPrompt = null;
let draggedFolder = null;
let deleteTarget = null;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    loadData();
    setupEventListeners();
});

// API calls
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showToast('An error occurred. Please try again.');
        return null;
    }
}

async function loadData() {
    const result = await apiCall('/api/data');
    if (result) {
        data = result;
        renderPromptList();
        renderMostUsed();
    }
}

// Event listeners
function setupEventListeners() {
    // Close modals when clicking outside
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            closeModal(e.target.id);
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                closeModal(openModal.id);
            }
        }
    });
}

// Search functionality
function handleSearch() {
    searchQuery = document.getElementById('searchInput').value;
    renderPromptList();
}

function getFilteredPrompts() {
    if (!searchQuery) return data.prompts;

    const nameMatches = data.prompts.filter(prompt => 
        prompt.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (nameMatches.length > 0) return nameMatches;

    return data.prompts.filter(prompt => 
        prompt.text.toLowerCase().includes(searchQuery.toLowerCase())
    );
}

// Helper function to build folder hierarchy
function buildFolderHierarchy() {
    const folderMap = {};
    const rootFolders = [];
    
    // Create folder map and initialize children arrays
    data.folders.forEach(folder => {
        folderMap[folder.id] = { ...folder, children: [] };
    });
    
    // Build hierarchy
    data.folders.forEach(folder => {
        if (folder.parentId && folderMap[folder.parentId]) {
            folderMap[folder.parentId].children.push(folderMap[folder.id]);
        } else {
            rootFolders.push(folderMap[folder.id]);
        }
    });
    
    // Sort each level by order
    function sortChildren(folders) {
        folders.sort((a, b) => (a.order || 0) - (b.order || 0));
        folders.forEach(folder => {
            if (folder.children.length > 0) {
                sortChildren(folder.children);
            }
        });
    }
    
    sortChildren(rootFolders);
    return rootFolders;
}

// Helper function to get all prompts in a folder (including subfolders)
function getPromptsInFolder(folderId, includeSubfolders = false) {
    let prompts = data.prompts.filter(p => p.folderId === folderId);
    
    if (includeSubfolders) {
        const subfolders = data.folders.filter(f => f.parentId === folderId);
        subfolders.forEach(subfolder => {
            prompts = prompts.concat(getPromptsInFolder(subfolder.id, true));
        });
    }
    
    return prompts;
}

// Render functions
function renderPromptList() {
    const container = document.getElementById('promptList');
    const filteredPrompts = getFilteredPrompts();
    
    // Get root level prompts
    const rootPrompts = filteredPrompts.filter(p => !p.folderId);
    
    let html = '';
    
    // Add root prompts
    html += '<div class="root-prompts" ondrop="handlePromptDrop(event)" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)">';
    rootPrompts.forEach(prompt => {
        html += renderPromptItem(prompt);
    });
    html += '</div>';
    
    // Add folders hierarchy
    const folderHierarchy = buildFolderHierarchy();
    html += renderFolderHierarchy(folderHierarchy, filteredPrompts);
    
    container.innerHTML = html;
}

function renderFolderHierarchy(folders, filteredPrompts, level = 0) {
    let html = '';
    
    folders.forEach((folder, index) => {
        html += renderFolderItem(folder, filteredPrompts, level, index, folders.length);
        
        if (folder.expanded && folder.children.length > 0) {
            html += '<div class="folder-children" style="margin-left: ' + (20 + level * 16) + 'px;">';
            html += renderFolderHierarchy(folder.children, filteredPrompts, level + 1);
            html += '</div>';
        }
    });
    
    return html;
}

function renderPromptItem(prompt) {
    const isSelected = selectedPrompt && selectedPrompt.id === prompt.id;
    
    return `
        <div class="prompt-item ${isSelected ? 'selected' : ''}" 
             draggable="true"
             ondragstart="handlePromptDragStart(event, '${prompt.id}')"
             ondragend="handleDragEnd(event)"
             onclick="selectPrompt('${prompt.id}')">
            <i class="fas fa-file-text"></i>
            <span class="prompt-name">${escapeHtml(prompt.name)}</span>
            <button class="delete-btn" onclick="event.stopPropagation(); confirmDeletePrompt('${prompt.id}', '${escapeHtml(prompt.name)}')">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
}

function renderFolderItem(folder, filteredPrompts, level, index, totalSiblings) {
    const isSelected = selectedFolder === folder.id;
    const icon = folder.expanded ? 'fa-folder-open' : 'fa-folder';
    const folderPrompts = getPromptsInFolder(folder.id, true);
    const promptCount = folderPrompts.length;
    
    // Check if folder can move up/down
    const canMoveUp = index > 0;
    const canMoveDown = index < totalSiblings - 1;
    
    let html = `
        <div class="folder-item ${isSelected ? 'selected' : ''}"
             ondrop="handleFolderDrop(event, '${folder.id}')"
             ondragover="handleDragOver(event)"
             ondragleave="handleDragLeave(event)"
             onclick="toggleFolder('${folder.id}')">
            <div class="folder-controls">
                <button class="folder-move-btn ${!canMoveUp ? 'disabled' : ''}" 
                        onclick="event.stopPropagation(); moveFolderUp('${folder.id}')"
                        ${!canMoveUp ? 'disabled' : ''}>
                    <i class="fas fa-chevron-up"></i>
                </button>
                <button class="folder-move-btn ${!canMoveDown ? 'disabled' : ''}" 
                        onclick="event.stopPropagation(); moveFolderDown('${folder.id}')"
                        ${!canMoveDown ? 'disabled' : ''}>
                    <i class="fas fa-chevron-down"></i>
                </button>
            </div>
            <i class="fas ${icon}"></i>
            <span class="folder-name">${escapeHtml(folder.name)}</span>
            <span class="folder-count">${promptCount}</span>
            <button class="delete-btn" onclick="event.stopPropagation(); confirmDeleteFolder('${folder.id}', '${escapeHtml(folder.name)}')">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    if (folder.expanded) {
        const directPrompts = filteredPrompts.filter(p => p.folderId === folder.id);
        if (directPrompts.length > 0) {
            html += '<div class="folder-children" style="margin-left: ' + (20 + level * 16) + 'px;">';
            directPrompts.forEach(prompt => {
                html += renderPromptItem(prompt);
            });
            html += '</div>';
        }
    }
    
    return html;
}

function renderMostUsed() {
    const mostUsedPrompts = [...data.prompts]
        .filter(prompt => prompt.usageCount > 0)
        .sort((a, b) => b.usageCount - a.usageCount);
    
    const container = document.getElementById('mostUsedList');
    const noUsageState = document.getElementById('noUsageState');
    
    if (mostUsedPrompts.length === 0) {
        container.style.display = 'none';
        noUsageState.style.display = 'flex';
        return;
    }
    
    container.style.display = 'block';
    noUsageState.style.display = 'none';
    
    let html = '';
    mostUsedPrompts.forEach((prompt, index) => {
        const preview = prompt.text.substring(0, 100) + (prompt.text.length > 100 ? '...' : '');
        html += `
            <div class="most-used-item" onclick="selectPromptFromMostUsed('${prompt.id}')">
                <div class="most-used-info">
                    <span class="rank-number">#${index + 1}</span>
                    <i class="fas fa-file-text"></i>
                    <div class="most-used-details">
                        <div class="most-used-name">${escapeHtml(prompt.name)}</div>
                        <div class="most-used-preview">${escapeHtml(preview)}</div>
                    </div>
                </div>
                <div class="most-used-actions">
                    <span class="usage-count">${prompt.usageCount} uses</span>
                    <button class="btn btn-outline" onclick="event.stopPropagation(); copyPromptById('${prompt.id}')">
                        <i class="fas fa-copy"></i>
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Selection functions
function selectPrompt(promptId) {
    selectedPrompt = data.prompts.find(p => p.id === promptId);
    selectedFolder = null;
    renderPromptList();
    showPromptDetails();
}

function selectPromptFromMostUsed(promptId) {
    selectPrompt(promptId);
    switchTab('repository');
}

function selectFolder(folderId) {
    selectedFolder = folderId;
    selectedPrompt = null;
    renderPromptList();
    showFolderDetails();
}

function toggleFolder(folderId) {
    const folder = data.folders.find(f => f.id === folderId);
    if (folder) {
        folder.expanded = !folder.expanded;
        if (selectedFolder === folderId && !folder.expanded) {
            selectedFolder = null;
            showEmptyState();
        } else if (selectedFolder !== folderId) {
            selectFolder(folderId);
        }
        renderPromptList();
    }
}

// Display functions
function showPromptDetails() {
    if (!selectedPrompt) return;
    
    document.getElementById('promptDetails').classList.remove('hidden');
    document.getElementById('folderDetails').classList.add('hidden');
    document.getElementById('emptyState').classList.add('hidden');
    
    document.getElementById('promptTitle').textContent = selectedPrompt.name;
    document.getElementById('promptText').textContent = selectedPrompt.text;
    
    // Update badges
    const badgesContainer = document.getElementById('promptBadges');
    let badges = '';
    
    if (selectedPrompt.versions && selectedPrompt.versions.length > 1) {
        badges += `<span class="prompt-badge version-info">v${selectedPrompt.currentVersion} of ${selectedPrompt.versions.length}</span>`;
    }
    
    if (selectedPrompt.usageCount > 0) {
        badges += `<span class="prompt-badge usage-info">Used ${selectedPrompt.usageCount} times</span>`;
    }
    
    badgesContainer.innerHTML = badges;
    
    // Show/hide history button
    const historyBtn = document.getElementById('historyBtn');
    if (selectedPrompt.versions && selectedPrompt.versions.length > 1) {
        historyBtn.classList.remove('hidden');
    } else {
        historyBtn.classList.add('hidden');
    }
}

function showFolderDetails() {
    if (!selectedFolder) return;
    
    const folder = data.folders.find(f => f.id === selectedFolder);
    if (!folder) return;
    
    document.getElementById('promptDetails').classList.add('hidden');
    document.getElementById('folderDetails').classList.remove('hidden');
    document.getElementById('emptyState').classList.add('hidden');
    
    document.getElementById('folderTitle').textContent = folder.name + ' Folder';
    
    const folderPrompts = getPromptsInFolder(selectedFolder, true);
    const container = document.getElementById('folderPrompts');
    
    let html = '';
    folderPrompts.forEach(prompt => {
        const usageBadge = prompt.usageCount > 0 
            ? `<span class="usage-badge">${prompt.usageCount}</span>` 
            : '';
        const versionBadge = prompt.versions && prompt.versions.length > 1 
            ? `<span class="version-badge">v${prompt.currentVersion}</span>` 
            : '';
        
        html += `
            <div class="folder-prompt-item" onclick="selectPrompt('${prompt.id}')">
                <div class="folder-prompt-info">
                    <i class="fas fa-file-text"></i>
                    <span>${escapeHtml(prompt.name)}</span>
                    ${versionBadge}
                    ${usageBadge}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function showEmptyState() {
    document.getElementById('promptDetails').classList.add('hidden');
    document.getElementById('folderDetails').classList.add('hidden');
    document.getElementById('emptyState').classList.remove('hidden');
}

// Tab switching
function switchTab(tabName) {
    activeTab = tabName;
    
    // Update tab triggers
    document.querySelectorAll('.tab-trigger').forEach(trigger => {
        trigger.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    if (tabName === 'most-used') {
        renderMostUsed();
    }
}

// Folder movement functions
async function moveFolderUp(folderId) {
    const result = await apiCall(`/api/folders/${folderId}/move-up`, {
        method: 'POST'
    });
    
    if (result && result.success) {
        await loadData();
        showToast('Folder moved up');
    }
}

async function moveFolderDown(folderId) {
    const result = await apiCall(`/api/folders/${folderId}/move-down`, {
        method: 'POST'
    });
    
    if (result && result.success) {
        await loadData();
        showToast('Folder moved down');
    }
}

// CRUD operations
async function addPrompt(event) {
    event.preventDefault();
    
    const name = document.getElementById('promptName').value;
    const text = document.getElementById('promptTextArea').value;
    
    const result = await apiCall('/api/prompts', {
        method: 'POST',
        body: JSON.stringify({
            name,
            text,
            folderId: selectedFolder
        })
    });
    
    if (result) {
        await loadData();
        closeModal('addPromptModal');
        showToast('Prompt added successfully');
        document.getElementById('promptName').value = '';
        document.getElementById('promptTextArea').value = '';
    }
}

async function addFolder(event) {
    event.preventDefault();
    
    const name = document.getElementById('folderName').value;
    
    const result = await apiCall('/api/folders', {
        method: 'POST',
        body: JSON.stringify({ 
            name,
            parentId: selectedFolder 
        })
    });
    
    if (result) {
        await loadData();
        closeModal('addFolderModal');
        showToast('Folder created successfully');
        document.getElementById('folderName').value = '';
    }
}

function editPrompt() {
    if (!selectedPrompt) return;
    
    document.getElementById('editPromptName').value = selectedPrompt.name;
    document.getElementById('editPromptText').value = selectedPrompt.text;
    showModal('editPromptModal');
}

async function saveEdit() {
    if (!selectedPrompt) return;
    
    const name = document.getElementById('editPromptName').value;
    const text = document.getElementById('editPromptText').value;
    
    const result = await apiCall(`/api/prompts/${selectedPrompt.id}`, {
        method: 'PUT',
        body: JSON.stringify({ name, text })
    });
    
    if (result) {
        await loadData();
        closeModal('editPromptModal');
        showToast('Prompt updated successfully');
        
        // Update selected prompt
        selectedPrompt = data.prompts.find(p => p.id === selectedPrompt.id);
        showPromptDetails();
    }
}

async function copyPrompt() {
    if (!selectedPrompt) return;
    await copyPromptById(selectedPrompt.id);
}

async function copyPromptById(promptId) {
    const prompt = data.prompts.find(p => p.id === promptId);
    if (!prompt) return;
    
    try {
        await navigator.clipboard.writeText(prompt.text);
        
        // Track usage
        await apiCall(`/api/prompts/${promptId}/copy`, {
            method: 'POST'
        });
        
        await loadData();
        showToast('Copied to clipboard');
        
        // Update display if this prompt is selected
        if (selectedPrompt && selectedPrompt.id === promptId) {
            selectedPrompt = data.prompts.find(p => p.id === promptId);
            showPromptDetails();
        }
        
        renderMostUsed();
    } catch (error) {
        showToast('Failed to copy to clipboard');
    }
}

// Delete functions
function confirmDeletePrompt(promptId, promptName) {
    deleteTarget = { type: 'prompt', id: promptId, name: promptName };
    document.getElementById('deleteMessage').innerHTML = `
        Are you sure you want to delete prompt "<strong>${escapeHtml(promptName)}</strong>"?
    `;
    showModal('deleteModal');
}

function confirmDeleteFolder(folderId, folderName) {
    deleteTarget = { type: 'folder', id: folderId, name: folderName };
    document.getElementById('deleteMessage').innerHTML = `
        Are you sure you want to delete folder "<strong>${escapeHtml(folderName)}</strong>"?
        <br><small>All prompts and subfolders will be moved to the parent folder.</small>
    `;
    showModal('deleteModal');
}

function deleteCurrentPrompt() {
    if (!selectedPrompt) return;
    confirmDeletePrompt(selectedPrompt.id, selectedPrompt.name);
}

async function confirmDelete() {
    if (!deleteTarget) return;
    
    let result;
    if (deleteTarget.type === 'prompt') {
        result = await apiCall(`/api/prompts/${deleteTarget.id}`, {
            method: 'DELETE'
        });
    } else {
        result = await apiCall(`/api/folders/${deleteTarget.id}`, {
            method: 'DELETE'
        });
    }
    
    if (result) {
        await loadData();
        closeModal('deleteModal');
        showToast(`${deleteTarget.type === 'prompt' ? 'Prompt' : 'Folder'} "${deleteTarget.name}" deleted successfully`);
        
        // Clear selection if deleted item was selected
        if (deleteTarget.type === 'prompt' && selectedPrompt && selectedPrompt.id === deleteTarget.id) {
            selectedPrompt = null;
            showEmptyState();
        } else if (deleteTarget.type === 'folder' && selectedFolder === deleteTarget.id) {
            selectedFolder = null;
            showEmptyState();
        }
        
        deleteTarget = null;
    }
}

// Version history
function showVersionHistory() {
    if (!selectedPrompt || !selectedPrompt.versions) return;
    
    document.getElementById('versionHistoryTitle').textContent = `Version History - ${selectedPrompt.name}`;
    
    const container = document.getElementById('versionsList');
    let html = '';
    
    const sortedVersions = [...selectedPrompt.versions].reverse();
    
    sortedVersions.forEach(version => {
        const isCurrent = version.version === selectedPrompt.currentVersion;
        const currentBadge = isCurrent ? '<span class="current-badge">Current</span>' : '';
        const restoreButton = !isCurrent ? 
            `<button class="btn btn-outline" onclick="restoreVersion('${selectedPrompt.id}', '${version.id}')">
                <i class="fas fa-undo"></i> Restore
            </button>` : '';
        
        html += `
            <div class="version-item">
                <div class="version-header">
                    <div class="version-info-left">
                        <span class="version-number">Version ${version.version}</span>
                        ${currentBadge}
                    </div>
                    <div class="version-info-right">
                        <span class="version-timestamp">${new Date(version.timestamp).toLocaleString()}</span>
                        ${restoreButton}
                    </div>
                </div>
                <div class="version-details">
                    <div class="version-field">
                        <span class="version-field-label">Name:</span>
                        <div class="version-field-content">${escapeHtml(version.name)}</div>
                    </div>
                    <div class="version-field">
                        <span class="version-field-label">Content:</span>
                        <div class="version-field-content">${escapeHtml(version.text)}</div>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    showModal('versionHistoryModal');
}

async function restoreVersion(promptId, versionId) {
    const result = await apiCall(`/api/prompts/${promptId}/restore/${versionId}`, {
        method: 'POST'
    });
    
    if (result) {
        await loadData();
        closeModal('versionHistoryModal');
        showToast('Version restored successfully');
        
        // Update selected prompt
        selectedPrompt = data.prompts.find(p => p.id === promptId);
        showPromptDetails();
    }
}

// Drag and drop for prompts
function handlePromptDragStart(event, promptId) {
    draggedPrompt = promptId;
    event.target.classList.add('dragging');
    event.dataTransfer.effectAllowed = 'move';
}

function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    if (!event.currentTarget.classList.contains('drag-over')) {
        event.currentTarget.classList.add('drag-over');
    }
}

function handleDragLeave(event) {
    // Only remove drag-over if we're actually leaving the element
    if (!event.currentTarget.contains(event.relatedTarget)) {
        event.currentTarget.classList.remove('drag-over');
    }
}

async function handlePromptDrop(event, folderId = null) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
    
    if (!draggedPrompt) return;
    
    const result = await apiCall(`/api/prompts/${draggedPrompt}/move`, {
        method: 'POST',
        body: JSON.stringify({ folderId })
    });
    
    if (result) {
        await loadData();
        showToast('Prompt moved successfully');
    }
    
    draggedPrompt = null;
}

// Drag and drop for folders (nesting)
async function handleFolderDrop(event, targetFolderId) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
    
    if (!draggedFolder || draggedFolder === targetFolderId) return;
    
    const result = await apiCall(`/api/folders/${draggedFolder}/move`, {
        method: 'POST',
        body: JSON.stringify({ parentId: targetFolderId })
    });
    
    if (result) {
        await loadData();
        showToast('Folder moved successfully');
    }
    
    draggedFolder = null;
}

function handleDragEnd(event) {
    event.target.classList.remove('dragging');
    // Clean up any remaining drag-over classes
    document.querySelectorAll('.drag-over').forEach(el => {
        el.classList.remove('drag-over');
    });
    draggedPrompt = null;
    draggedFolder = null;
}

// Modal functions
function showModal(modalId) {
    document.getElementById(modalId).classList.add('show');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

function showAddPromptModal() {
    showModal('addPromptModal');
}

function showAddFolderModal() {
    showModal('addFolderModal');
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('open');
}

// Initialize empty state
showEmptyState();
