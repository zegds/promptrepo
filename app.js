let config = {};
let selectedFolder = null;
let selectedPrompt = null;

window.onload = async () => {
  const res = await fetch('/get_config');
  config = await res.json();
  renderFolders();
};

li.contentEditable = true;
li.onblur = () => renameFolder(li.innerText, folder);
function renameFolder(newName, oldName) {
  if (newName === oldName || !newName.trim()) return;
  if (config.folders[newName]) {
    alert("Folder name already exists.");
    renderFolders();
    return;
  }
  config.folders[newName] = config.folders[oldName];
  delete config.folders[oldName];

  if (selectedFolder === oldName) selectedFolder = newName;

  saveConfig();
  renderFolders();
}
function renamePrompt(index, newName) {
  config.folders[selectedFolder][index].title = newName.trim();
  saveConfig();
}

function renderFolders() {
  const list = document.getElementById('folder-list');
  list.innerHTML = '';
  for (const folder in config.folders) {
    const li = document.createElement('li');
    li.innerText = folder;
    li.onclick = () => {
      selectedFolder = folder;
      renderPrompts();
    };
    list.appendChild(li);
  }
}

function renderPrompts() {
  const container = document.getElementById('prompt-list');
  container.innerHTML = '';
  const prompts = config.folders[selectedFolder];
  prompts.forEach((prompt, idx) => {
    const div = document.createElement('div');
    div.classList.add('prompt-item');
    div.setAttribute('draggable', true);
    div.dataset.index = idx;
    div.dataset.folder = selectedFolder;
    div.ondragstart = dragPrompt;

    div.innerHTML = `
      <span contenteditable="true" onblur="renamePrompt(${idx}, this.innerText)">${prompt.title}</span>
      <button onclick="editPrompt(${idx})">Edit</button>
      <button onclick="copyPrompt(${idx})">Copy</button>
      <button onclick="confirmDeletePrompt(${idx})">🗑️</button>
    `;
    container.appendChild(div);
  });
}

function dragPrompt(event) {
  const index = event.target.dataset.index;
  const folder = event.target.dataset.folder;
  event.dataTransfer.setData("text/plain", JSON.stringify({ index, folder }));
}

li.ondrop = dropPrompt;
li.ondragover = (e) => e.preventDefault();
function dropPrompt(event) {
  event.preventDefault();
  const data = JSON.parse(event.dataTransfer.getData("text/plain"));
  const fromFolder = data.folder;
  const index = data.index;
  const prompt = config.folders[fromFolder][index];

  const toFolder = event.target.innerText;
  if (!config.folders[toFolder]) return;

  // Move prompt
  config.folders[fromFolder].splice(index, 1);
  config.folders[toFolder].push(prompt);

  saveConfig();
  renderFolders();
  if (selectedFolder === fromFolder || selectedFolder === toFolder) {
    renderPrompts();
  }
}

function addFolder() {
  const name = prompt("Folder name:");
  if (name) {
    config.folders[name] = [];
    saveConfig();
    renderFolders();
  }
}

function addPrompt() {
  selectedPrompt = null;
  document.getElementById('prompt-title').value = '';
  document.getElementById('prompt-text').value = '';
  document.getElementById('prompt-editor').style.display = 'block';
}

function editPrompt(index) {
  selectedPrompt = index;
  const prompt = config.folders[selectedFolder][index];
  document.getElementById('prompt-title').value = prompt.title;
  document.getElementById('prompt-text').value = prompt.text;
  document.getElementById('prompt-editor').style.display = 'block';
}

function savePrompt() {
  const title = document.getElementById('prompt-title').value;
  const text = document.getElementById('prompt-text').value;
  if (selectedPrompt != null) {
    config.folders[selectedFolder][selectedPrompt] = { title, text };
  } else {
    config.folders[selectedFolder].push({ title, text });
  }
  document.getElementById('prompt-editor').style.display = 'none';
  saveConfig();
  renderPrompts();
}

function copyPrompt(index) {
  navigator.clipboard.writeText(config.folders[selectedFolder][index].text);
}

function searchPrompts() {
  const term = document.getElementById('search-bar').value.toLowerCase();
  const results = [];

  for (const folder in config.folders) {
    for (const prompt of config.folders[folder]) {
      if (prompt.title.toLowerCase().includes(term)) {
        results.push(prompt);
      }
    }
  }

  if (results.length === 0) {
    for (const folder in config.folders) {
      for (const prompt of config.folders[folder]) {
        if (prompt.text.toLowerCase().includes(term)) {
          results.push(prompt);
        }
      }
    }
  }

  const container = document.getElementById('prompt-list');
  container.innerHTML = '';
  results.forEach(prompt => {
    const div = document.createElement('div');
    div.innerHTML = `<b>${prompt.title}</b> <button onclick="copyPromptText('${prompt.text}')">Copy</button>`;
    container.appendChild(div);
  });
}

function copyPromptText(text) {
  navigator.clipboard.writeText(text);
}

async function saveConfig() {
  await fetch('/save_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
}
