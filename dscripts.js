// Global variables
let currentPrompt = null
let currentFolder = null
let folders = []
let prompts = []
let draggedElement = null
let draggedType = null // 'folder' or 'prompt'

// Initialize the application
document.addEventListener("DOMContentLoaded", () => {
  loadData()
  setupEventListeners()
  setupSearch()
  setupTabs()
})

// Load data from the server
function loadData() {
  Promise.all([fetch("/api/prompts").then((r) => r.json()), fetch("/api/folders").then((r) => r.json())])
    .then(([promptsData, foldersData]) => {
      prompts = promptsData
      folders = foldersData
      renderSidebar()
      renderMostUsed()
    })
    .catch((error) => {
      console.error("Error loading data:", error)
      showToast("Error loading data")
    })
}

// Setup event listeners
function setupEventListeners() {
  // Sidebar toggle
  document.getElementById("sidebarToggle").addEventListener("click", toggleSidebar)

  // Add prompt button
  document.getElementById("addPromptBtn").addEventListener("click", showAddPromptModal)

  // Add folder button
  document.getElementById("addFolderBtn").addEventListener("click", showAddFolderModal)

  // Modal close buttons
  document.querySelectorAll(".modal-close").forEach((btn) => {
    btn.addEventListener("click", closeModals)
  })

  // Modal background clicks
  document.querySelectorAll(".modal").forEach((modal) => {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModals()
    })
  })

  // Form submissions
  document.getElementById("promptForm").addEventListener("submit", handlePromptSubmit)
  document.getElementById("folderForm").addEventListener("submit", handleFolderSubmit)
  document.getElementById("editPromptForm").addEventListener("submit", handleEditPromptSubmit)
  document.getElementById("editFolderForm").addEventListener("submit", handleEditFolderSubmit)
}

// Setup search functionality
function setupSearch() {
  const searchInput = document.getElementById("searchInput")
  searchInput.addEventListener("input", function () {
    const query = this.value.toLowerCase()
    filterSidebar(query)
  })
}

// Setup tabs
function setupTabs() {
  document.querySelectorAll(".tab-trigger").forEach((trigger) => {
    trigger.addEventListener("click", function () {
      const tabId = this.dataset.tab
      switchTab(tabId)
    })
  })
}

// Render sidebar with folders and prompts
function renderSidebar() {
  const foldersContainer = document.getElementById("foldersContainer")
  const promptsContainer = document.getElementById("promptsContainer")

  // Render folders (only root level folders)
  const rootFolders = folders.filter((f) => !f.parent_id).sort((a, b) => (a.order || 0) - (b.order || 0))
  foldersContainer.innerHTML = rootFolders.map((folder) => renderFolder(folder)).join("")

  // Render root level prompts (prompts not in any folder)
  const rootPrompts = prompts.filter((p) => !p.folder_id)
  promptsContainer.innerHTML = `
        <div class="root-prompts" data-drop-zone="root">
            ${rootPrompts.map((prompt) => renderPrompt(prompt)).join("")}
        </div>
    `

  setupDragAndDrop()
}

// Render a single folder with its children
function renderFolder(folder, level = 0) {
  const childFolders = folders.filter((f) => f.parent_id === folder.id).sort((a, b) => (a.order || 0) - (b.order || 0))
  const folderPrompts = prompts.filter((p) => p.folder_id === folder.id)
  const totalPrompts = folderPrompts.length + getNestedPromptCount(folder.id)

  const isNested = level > 0
  const indentClass = level > 0 ? "folder-children" : ""

  return `
        <div class="folder-item ${indentClass}" 
             data-folder-id="${folder.id}" 
             data-level="${level}"
             draggable="true">
            <i class="fas fa-folder"></i>
            <span class="folder-name">${folder.name}</span>
            <span class="folder-count">${totalPrompts}</span>
            <div class="folder-controls">
                ${renderFolderControls(folder, level)}
            </div>
            <button class="delete-btn" onclick="deleteFolder(${folder.id})">
                <i class="fas fa-times"></i>
            </button>
        </div>
        ${childFolders.map((child) => renderFolder(child, level + 1)).join("")}
        ${
          folderPrompts.length > 0
            ? `
            <div class="folder-prompts-container" data-folder-id="${folder.id}">
                ${folderPrompts.map((prompt) => renderPrompt(prompt, level + 1)).join("")}
            </div>
        `
            : ""
        }
    `
}

// Render folder control buttons (up/down/out arrows)
function renderFolderControls(folder, level) {
  const siblings = folders.filter((f) => f.parent_id === folder.parent_id)
  const currentIndex = siblings.findIndex((f) => f.id === folder.id)
  const isFirst = currentIndex === 0
  const isLast = currentIndex === siblings.length - 1
  const isNested = level > 0

  return `
        <button class="folder-move-btn ${isFirst ? "disabled" : ""}" 
                onclick="moveFolderUp(${folder.id})" 
                ${isFirst ? "disabled" : ""}>
            <i class="fas fa-chevron-up"></i>
        </button>
        <button class="folder-move-btn ${isLast ? "disabled" : ""}" 
                onclick="moveFolderDown(${folder.id})" 
                ${isLast ? "disabled" : ""}>
            <i class="fas fa-chevron-down"></i>
        </button>
        ${
          isNested
            ? `
            <button class="folder-move-btn" onclick="moveFolderOut(${folder.id})">
                <i class="fas fa-arrow-left"></i>
            </button>
        `
            : ""
        }
    `
}

// Render a single prompt
function renderPrompt(prompt, level = 0) {
  const indentClass = level > 0 ? "folder-children" : ""
  return `
        <div class="prompt-item ${indentClass} ${currentPrompt?.id === prompt.id ? "selected" : ""}" 
             data-prompt-id="${prompt.id}"
             data-level="${level}"
             draggable="true"
             onclick="selectPrompt(${prompt.id})">
            <i class="fas fa-file-text"></i>
            <span class="prompt-name">${prompt.name}</span>
            <button class="delete-btn" onclick="deletePrompt(${prompt.id})">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `
}

// Setup drag and drop functionality
function setupDragAndDrop() {
  // Setup draggable elements
  document.querySelectorAll(".folder-item, .prompt-item").forEach((item) => {
    item.addEventListener("dragstart", handleDragStart)
    item.addEventListener("dragend", handleDragEnd)
  })

  // Setup drop zones
  document.querySelectorAll(".folder-item, .root-prompts").forEach((zone) => {
    zone.addEventListener("dragover", handleDragOver)
    zone.addEventListener("drop", handleDrop)
    zone.addEventListener("dragenter", handleDragEnter)
    zone.addEventListener("dragleave", handleDragLeave)
  })
}

// Handle drag start
function handleDragStart(e) {
  draggedElement = e.target
  draggedType = e.target.classList.contains("folder-item") ? "folder" : "prompt"

  e.target.classList.add("dragging")
  e.dataTransfer.effectAllowed = "move"

  // Set drag data
  if (draggedType === "folder") {
    e.dataTransfer.setData("text/plain", `folder:${e.target.dataset.folderId}`)
  } else {
    e.dataTransfer.setData("text/plain", `prompt:${e.target.dataset.promptId}`)
  }
}

// Handle drag end
function handleDragEnd(e) {
  e.target.classList.remove("dragging")

  // Remove all drag-over classes
  document.querySelectorAll(".drag-over").forEach((el) => {
    el.classList.remove("drag-over")
  })

  draggedElement = null
  draggedType = null
}

// Handle drag over
function handleDragOver(e) {
  e.preventDefault()
  e.dataTransfer.dropEffect = "move"
}

// Handle drag enter
function handleDragEnter(e) {
  e.preventDefault()

  if (canDropOn(e.target)) {
    e.target.classList.add("drag-over")
  }
}

// Handle drag leave
function handleDragLeave(e) {
  // Only remove drag-over if we're actually leaving the element
  if (!e.currentTarget.contains(e.relatedTarget)) {
    e.currentTarget.classList.remove("drag-over")
  }
}

// Handle drop
function handleDrop(e) {
  e.preventDefault()
  e.stopPropagation()

  const dropTarget = e.currentTarget
  dropTarget.classList.remove("drag-over")

  if (!canDropOn(dropTarget) || !draggedElement) return

  const dragData = e.dataTransfer.getData("text/plain")
  const [dragType, dragId] = dragData.split(":")

  if (dragType === "folder") {
    handleFolderDrop(Number.parseInt(dragId), dropTarget)
  } else if (dragType === "prompt") {
    handlePromptDrop(Number.parseInt(dragId), dropTarget)
  }
}

// Check if we can drop on the target
function canDropOn(target) {
  if (!draggedElement) return false

  // Can't drop on self
  if (target === draggedElement) return false

  // If dragging a folder
  if (draggedType === "folder") {
    const draggedFolderId = Number.parseInt(draggedElement.dataset.folderId)

    // Can't drop folder on its own children
    if (target.classList.contains("folder-item")) {
      const targetFolderId = Number.parseInt(target.dataset.folderId)
      if (isChildFolder(targetFolderId, draggedFolderId)) return false
    }

    // Can drop on other folders or root
    return target.classList.contains("folder-item") || target.classList.contains("root-prompts")
  }

  // If dragging a prompt
  if (draggedType === "prompt") {
    // Can drop on folders or root
    return target.classList.contains("folder-item") || target.classList.contains("root-prompts")
  }

  return false
}

// Handle folder drop
function handleFolderDrop(folderId, dropTarget) {
  let newParentId = null

  if (dropTarget.classList.contains("folder-item")) {
    newParentId = Number.parseInt(dropTarget.dataset.folderId)
  }

  // Update folder parent
  fetch("/api/folders/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      folder_id: folderId,
      parent_id: newParentId,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        loadData() // Reload to reflect changes
        showToast("Folder moved successfully")
      } else {
        showToast("Error moving folder")
      }
    })
    .catch((error) => {
      console.error("Error moving folder:", error)
      showToast("Error moving folder")
    })
}

// Handle prompt drop
function handlePromptDrop(promptId, dropTarget) {
  let newFolderId = null

  if (dropTarget.classList.contains("folder-item")) {
    newFolderId = Number.parseInt(dropTarget.dataset.folderId)
  }

  // Update prompt folder
  fetch("/api/prompts/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt_id: promptId,
      folder_id: newFolderId,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        loadData() // Reload to reflect changes
        showToast("Prompt moved successfully")
      } else {
        showToast("Error moving prompt")
      }
    })
    .catch((error) => {
      console.error("Error moving prompt:", error)
      showToast("Error moving prompt")
    })
}

// Check if targetId is a child of parentId
function isChildFolder(targetId, parentId) {
  const targetFolder = folders.find((f) => f.id === targetId)
  if (!targetFolder) return false

  if (targetFolder.parent_id === parentId) return true
  if (targetFolder.parent_id) {
    return isChildFolder(targetFolder.parent_id, parentId)
  }

  return false
}

// Get nested prompt count for a folder
function getNestedPromptCount(folderId) {
  const childFolders = folders.filter((f) => f.parent_id === folderId)
  let count = 0

  childFolders.forEach((child) => {
    count += prompts.filter((p) => p.folder_id === child.id).length
    count += getNestedPromptCount(child.id)
  })

  return count
}

// Move folder up
function moveFolderUp(folderId) {
  const folder = folders.find((f) => f.id === folderId)
  const siblings = folders.filter((f) => f.parent_id === folder.parent_id)
  const currentIndex = siblings.findIndex((f) => f.id === folderId)

  if (currentIndex > 0) {
    // Swap orders
    const prevFolder = siblings[currentIndex - 1]
    const tempOrder = folder.order || currentIndex

    fetch("/api/folders/reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        folder_id: folderId,
        new_order: prevFolder.order || currentIndex - 1,
      }),
    })
      .then(() => {
        return fetch("/api/folders/reorder", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            folder_id: prevFolder.id,
            new_order: tempOrder,
          }),
        })
      })
      .then(() => {
        loadData()
        showToast("Folder moved up")
      })
      .catch((error) => {
        console.error("Error moving folder:", error)
        showToast("Error moving folder")
      })
  }
}

// Move folder down
function moveFolderDown(folderId) {
  const folder = folders.find((f) => f.id === folderId)
  const siblings = folders.filter((f) => f.parent_id === folder.parent_id)
  const currentIndex = siblings.findIndex((f) => f.id === folderId)

  if (currentIndex < siblings.length - 1) {
    // Swap orders
    const nextFolder = siblings[currentIndex + 1]
    const tempOrder = folder.order || currentIndex

    fetch("/api/folders/reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        folder_id: folderId,
        new_order: nextFolder.order || currentIndex + 1,
      }),
    })
      .then(() => {
        return fetch("/api/folders/reorder", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            folder_id: nextFolder.id,
            new_order: tempOrder,
          }),
        })
      })
      .then(() => {
        loadData()
        showToast("Folder moved down")
      })
      .catch((error) => {
        console.error("Error moving folder:", error)
        showToast("Error moving folder")
      })
  }
}

// Move folder out (remove nesting)
function moveFolderOut(folderId) {
  const folder = folders.find((f) => f.id === folderId)
  const parentFolder = folders.find((f) => f.id === folder.parent_id)

  fetch("/api/folders/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      folder_id: folderId,
      parent_id: parentFolder ? parentFolder.parent_id : null,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        loadData()
        showToast("Folder moved out")
      } else {
        showToast("Error moving folder")
      }
    })
    .catch((error) => {
      console.error("Error moving folder:", error)
      showToast("Error moving folder")
    })
}

// Select prompt
function selectPrompt(promptId) {
  currentPrompt = prompts.find((p) => p.id === promptId)
  if (currentPrompt) {
    renderPromptDetails()
    renderSidebar() // Re-render to update selection
    switchTab("prompt")
  }
}

// Select folder
function selectFolder(folderId) {
  currentFolder = folders.find((f) => f.id === folderId)
  if (currentFolder) {
    renderFolderDetails()
    switchTab("folder")
  }
}

// Render prompt details
function renderPromptDetails() {
  if (!currentPrompt) return

  const container = document.getElementById("promptDetails")
  container.innerHTML = `
        <div class="prompt-header">
            <div class="prompt-title-section">
                <h2>${currentPrompt.name}</h2>
                <div class="prompt-badges">
                    <span class="prompt-badge version-info">v${currentPrompt.version}</span>
                    <span class="prompt-badge usage-info">${currentPrompt.usage_count} uses</span>
                </div>
            </div>
            <div class="prompt-actions">
                <button class="btn btn-outline" onclick="copyPrompt()">
                    <i class="fas fa-copy"></i> Copy
                </button>
                <button class="btn btn-outline" onclick="showEditPromptModal(${currentPrompt.id})">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn btn-outline" onclick="showVersionHistory(${currentPrompt.id})">
                    <i class="fas fa-history"></i> History
                </button>
                <button class="btn btn-danger" onclick="deletePrompt(${currentPrompt.id})">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
        <div class="prompt-content">
            <pre>${currentPrompt.content}</pre>
            <button class="prompt-copy-btn" onclick="copyPrompt()">
                <i class="fas fa-copy"></i>
            </button>
        </div>
    `
}

// Render folder details
function renderFolderDetails() {
  if (!currentFolder) return

  const folderPrompts = prompts.filter((p) => p.folder_id === currentFolder.id)

  const container = document.getElementById("folderDetails")
  container.innerHTML = `
        <h2>${currentFolder.name}</h2>
        <div class="folder-prompts">
            ${
              folderPrompts.length > 0
                ? folderPrompts
                    .map(
                      (prompt) => `
                    <div class="folder-prompt-item" onclick="selectPrompt(${prompt.id})">
                        <div class="folder-prompt-info">
                            <i class="fas fa-file-text"></i>
                            <span>${prompt.name}</span>
                        </div>
                        <div class="prompt-badges">
                            <span class="prompt-badge version-info">v${prompt.version}</span>
                            <span class="prompt-badge usage-info">${prompt.usage_count} uses</span>
                        </div>
                    </div>
                `,
                    )
                    .join("")
                : '<div class="empty-state"><div class="empty-icon"><i class="fas fa-folder-open"></i></div><p>No prompts in this folder</p></div>'
            }
        </div>
    `
}

// Render most used prompts
function renderMostUsed() {
  const mostUsed = [...prompts]
    .filter((p) => p.usage_count > 0)
    .sort((a, b) => b.usage_count - a.usage_count)
    .slice(0, 10)

  const container = document.getElementById("mostUsedList")

  if (mostUsed.length === 0) {
    container.innerHTML = `
            <div class="no-usage-state">
                <i class="fas fa-chart-bar"></i>
                <h3>No Usage Data</h3>
                <p>Start using prompts to see your most used ones here.</p>
            </div>
        `
    return
  }

  container.innerHTML = mostUsed
    .map(
      (prompt, index) => `
        <div class="most-used-item" onclick="selectPrompt(${prompt.id})">
            <div class="most-used-info">
                <div class="rank-number">${index + 1}</div>
                <div class="most-used-details">
                    <div class="most-used-name">${prompt.name}</div>
                    <div class="most-used-preview">${prompt.content.substring(0, 100)}...</div>
                </div>
            </div>
            <div class="most-used-actions">
                <span class="usage-count">${prompt.usage_count} uses</span>
                <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); copyPromptById(${prompt.id})">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        </div>
    `,
    )
    .join("")
}

// Switch tabs
function switchTab(tabId) {
  // Update tab triggers
  document.querySelectorAll(".tab-trigger").forEach((trigger) => {
    trigger.classList.remove("active")
  })
  document.querySelector(`[data-tab="${tabId}"]`).classList.add("active")

  // Update tab content
  document.querySelectorAll(".tab-content").forEach((content) => {
    content.classList.remove("active")
  })
  document.getElementById(`${tabId}Tab`).classList.add("active")
}

// Filter sidebar based on search
function filterSidebar(query) {
  const items = document.querySelectorAll(".prompt-item, .folder-item")

  items.forEach((item) => {
    const name = item.querySelector(".prompt-name, .folder-name").textContent.toLowerCase()
    const matches = name.includes(query)
    item.style.display = matches ? "flex" : "none"
  })
}

// Toggle sidebar (mobile)
function toggleSidebar() {
  document.querySelector(".sidebar").classList.toggle("open")
}

// Copy prompt content
function copyPrompt() {
  if (!currentPrompt) return

  navigator.clipboard
    .writeText(currentPrompt.content)
    .then(() => {
      showToast("Prompt copied to clipboard")

      // Increment usage count
      fetch(`/api/prompts/${currentPrompt.id}/use`, { method: "POST" }).then(() => {
        currentPrompt.usage_count++
        renderPromptDetails()
        renderMostUsed()
      })
    })
    .catch(() => {
      showToast("Failed to copy prompt")
    })
}

// Copy prompt by ID
function copyPromptById(promptId) {
  const prompt = prompts.find((p) => p.id === promptId)
  if (!prompt) return

  navigator.clipboard
    .writeText(prompt.content)
    .then(() => {
      showToast("Prompt copied to clipboard")

      // Increment usage count
      fetch(`/api/prompts/${promptId}/use`, { method: "POST" }).then(() => {
        prompt.usage_count++
        renderMostUsed()
        if (currentPrompt && currentPrompt.id === promptId) {
          renderPromptDetails()
        }
      })
    })
    .catch(() => {
      showToast("Failed to copy prompt")
    })
}

// Show toast notification
function showToast(message) {
  const toast = document.getElementById("toast")
  toast.textContent = message
  toast.classList.add("show")

  setTimeout(() => {
    toast.classList.remove("show")
  }, 3000)
}

// Modal functions
function showAddPromptModal() {
  document.getElementById("addPromptModal").classList.add("show")
}

function showAddFolderModal() {
  document.getElementById("addFolderModal").classList.add("show")
}

function showEditPromptModal(promptId) {
  const prompt = prompts.find((p) => p.id === promptId)
  if (!prompt) return

  document.getElementById("editPromptName").value = prompt.name
  document.getElementById("editPromptContent").value = prompt.content
  document.getElementById("editPromptId").value = prompt.id
  document.getElementById("editPromptModal").classList.add("show")
}

function showEditFolderModal(folderId) {
  const folder = folders.find((f) => f.id === folderId)
  if (!folder) return

  document.getElementById("editFolderName").value = folder.name
  document.getElementById("editFolderId").value = folder.id
  document.getElementById("editFolderModal").classList.add("show")
}

function showVersionHistory(promptId) {
  fetch(`/api/prompts/${promptId}/versions`)
    .then((response) => response.json())
    .then((versions) => {
      const container = document.getElementById("versionsList")
      container.innerHTML = versions
        .map(
          (version) => `
                <div class="version-item">
                    <div class="version-header">
                        <div class="version-info-left">
                            <span class="version-number">v${version.version}</span>
                            ${version.is_current ? '<span class="current-badge">Current</span>' : ""}
                        </div>
                        <div class="version-info-right">
                            <span class="version-timestamp">${new Date(version.created_at).toLocaleDateString()}</span>
                            <button class="btn btn-outline btn-sm" onclick="revertToVersion(${promptId}, ${version.version})">
                                Revert
                            </button>
                        </div>
                    </div>
                    <div class="version-details">
                        <div class="version-field">
                            <div class="version-field-label">Name:</div>
                            <div class="version-field-content">${version.name}</div>
                        </div>
                        <div class="version-field">
                            <div class="version-field-label">Content:</div>
                            <div class="version-field-content">${version.content}</div>
                        </div>
                    </div>
                </div>
            `,
        )
        .join("")

      document.getElementById("versionHistoryModal").classList.add("show")
    })
    .catch((error) => {
      console.error("Error loading version history:", error)
      showToast("Error loading version history")
    })
}

function closeModals() {
  document.querySelectorAll(".modal").forEach((modal) => {
    modal.classList.remove("show")
  })
}

// Form handlers
function handlePromptSubmit(e) {
  e.preventDefault()

  const formData = new FormData(e.target)
  const data = {
    name: formData.get("name"),
    content: formData.get("content"),
  }

  fetch("/api/prompts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
    .then((response) => response.json())
    .then((result) => {
      if (result.success) {
        closeModals()
        loadData()
        showToast("Prompt added successfully")
        e.target.reset()
      } else {
        showToast("Error adding prompt")
      }
    })
    .catch((error) => {
      console.error("Error adding prompt:", error)
      showToast("Error adding prompt")
    })
}

function handleFolderSubmit(e) {
  e.preventDefault()

  const formData = new FormData(e.target)
  const data = {
    name: formData.get("name"),
  }

  fetch("/api/folders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
    .then((response) => response.json())
    .then((result) => {
      if (result.success) {
        closeModals()
        loadData()
        showToast("Folder added successfully")
        e.target.reset()
      } else {
        showToast("Error adding folder")
      }
    })
    .catch((error) => {
      console.error("Error adding folder:", error)
      showToast("Error adding folder")
    })
}

function handleEditPromptSubmit(e) {
  e.preventDefault()

  const formData = new FormData(e.target)
  const promptId = formData.get("id")
  const data = {
    name: formData.get("name"),
    content: formData.get("content"),
  }

  fetch(`/api/prompts/${promptId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
    .then((response) => response.json())
    .then((result) => {
      if (result.success) {
        closeModals()
        loadData()
        showToast("Prompt updated successfully")
      } else {
        showToast("Error updating prompt")
      }
    })
    .catch((error) => {
      console.error("Error updating prompt:", error)
      showToast("Error updating prompt")
    })
}

function handleEditFolderSubmit(e) {
  e.preventDefault()

  const formData = new FormData(e.target)
  const folderId = formData.get("id")
  const data = {
    name: formData.get("name"),
  }

  fetch(`/api/folders/${folderId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
    .then((response) => response.json())
    .then((result) => {
      if (result.success) {
        closeModals()
        loadData()
        showToast("Folder updated successfully")
      } else {
        showToast("Error updating folder")
      }
    })
    .catch((error) => {
      console.error("Error updating folder:", error)
      showToast("Error updating folder")
    })
}

// Delete functions
function deletePrompt(promptId) {
  if (!confirm("Are you sure you want to delete this prompt?")) return

  fetch(`/api/prompts/${promptId}`, { method: "DELETE" })
    .then((response) => response.json())
    .then((result) => {
      if (result.success) {
        loadData()
        showToast("Prompt deleted successfully")

        // Clear current prompt if it was deleted
        if (currentPrompt && currentPrompt.id === promptId) {
          currentPrompt = null
          switchTab("mostUsed")
        }
      } else {
        showToast("Error deleting prompt")
      }
    })
    .catch((error) => {
      console.error("Error deleting prompt:", error)
      showToast("Error deleting prompt")
    })
}

function deleteFolder(folderId) {
  if (
    !confirm("Are you sure you want to delete this folder? All prompts in this folder will be moved to the root level.")
  )
    return

  fetch(`/api/folders/${folderId}`, { method: "DELETE" })
    .then((response) => response.json())
    .then((result) => {
      if (result.success) {
        loadData()
        showToast("Folder deleted successfully")

        // Clear current folder if it was deleted
        if (currentFolder && currentFolder.id === folderId) {
          currentFolder = null
          switchTab("mostUsed")
        }
      } else {
        showToast("Error deleting folder")
      }
    })
    .catch((error) => {
      console.error("Error deleting folder:", error)
      showToast("Error deleting folder")
    })
}

function revertToVersion(promptId, version) {
  if (!confirm(`Are you sure you want to revert to version ${version}?`)) return

  fetch(`/api/prompts/${promptId}/revert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ version }),
  })
    .then((response) => response.json())
    .then((result) => {
      if (result.success) {
        closeModals()
        loadData()
        showToast(`Reverted to version ${version}`)
      } else {
        showToast("Error reverting version")
      }
    })
    .catch((error) => {
      console.error("Error reverting version:", error)
      showToast("Error reverting version")
    })
}
