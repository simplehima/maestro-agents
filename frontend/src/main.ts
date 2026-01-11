import './style.css';

const isProd = window.location.port !== '5173';
const API_URL = isProd ? `${window.location.protocol}//${window.location.host}` : 'http://localhost:8000';
const WS_URL = isProd ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws` : 'ws://localhost:8000/ws';

let socket: WebSocket | null = null;
let currentProjectId: string | null = null;
let reconnectAttempts = 0;

// DOM Elements
const backendStatus = document.getElementById('backend-status');
const objectiveInput = document.getElementById('objective-input') as HTMLTextAreaElement;
const projectNameInput = document.getElementById('project-name') as HTMLInputElement;
const startBtn = document.getElementById('start-btn') as HTMLButtonElement;
const guidanceInput = document.getElementById('guidance-input') as HTMLInputElement;
const guideBtn = document.getElementById('guide-btn') as HTMLButtonElement;
const logsContainer = document.getElementById('logs-container') as HTMLDivElement;
const clearFeedBtn = document.getElementById('clear-feed');
const modelPresetSelect = document.getElementById('model-preset') as HTMLSelectElement;
const recentProjectsContainer = document.getElementById('recent-projects');
const projectsGrid = document.getElementById('projects-grid');

// Initialize Lucide icons
declare const lucide: { createIcons: () => void };
document.addEventListener('DOMContentLoaded', () => {
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }
});

// === WebSocket Connection ===
function connectWS() {
  socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    reconnectAttempts = 0;
    updateBackendStatus(true);
    addLog('System', 'Connected to Maestro backend');
  };

  socket.onclose = () => {
    updateBackendStatus(false);
    addLog('System', 'Disconnected. Reconnecting...');

    const delay = Math.min(3000 * Math.pow(2, reconnectAttempts), 30000);
    reconnectAttempts++;
    setTimeout(connectWS, delay);
  };

  socket.onerror = () => {
    socket?.close();
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleSocketMessage(data);
  };
}

function updateBackendStatus(online: boolean) {
  const dot = backendStatus?.querySelector('.dot');
  const text = backendStatus?.querySelector('span:last-child');

  if (dot) {
    dot.classList.toggle('online', online);
    dot.classList.toggle('offline', !online);
  }
  if (text) {
    text.textContent = online ? 'Connected' : 'Disconnected';
  }
}

function handleSocketMessage(data: any) {
  switch (data.type) {
    case 'log':
      addLog(data.agent, data.text, data.status);
      updateAgentStatus(data.agent, data.text, data.status);
      break;
    case 'final_output':
      showFinalOutput(data.text, data.outputPath);
      resetAgents();
      enableStartButton();
      break;
  }
}

// === Logging ===
function addLog(agent: string, text: string, _status?: string) {
  const entry = document.createElement('div');
  const agentClass = agent.toLowerCase().replace(/[\/\s]/g, '-');
  entry.className = `log-entry ${agentClass}`;

  const iconName = getAgentIcon(agent);

  entry.innerHTML = `
        <span class="log-icon"><i data-lucide="${iconName}"></i></span>
        <div class="log-content">
            <div class="log-agent">${agent}</div>
            <div class="log-text">${text}</div>
        </div>
    `;

  logsContainer.prepend(entry);

  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }
}

function getAgentIcon(agent: string): string {
  const icons: Record<string, string> = {
    'System': 'info',
    'Orchestrator': 'brain',
    'Research': 'search',
    'UI/UX Designer': 'palette',
    'Developer': 'code-2',
    'Security': 'lock',
    'QA Tester': 'shield-check',
    'Documentation': 'file-text',
    'User': 'user',
    'Refiner': 'sparkles'
  };
  return icons[agent] || 'message-circle';
}

// Agent mapping for LED IDs
const agentToLedId: { [key: string]: string } = {
  'Orchestrator': 'led-orchestrator',
  'Research': 'led-research',
  'UI/UX Designer': 'led-uiux',
  'Developer': 'led-developer',
  'Security': 'led-security',
  'QA Tester': 'led-qa',
  'Documentation': 'led-docs',
  'Refiner': 'led-refiner'
};

function updateAgentStatus(agent: string, text: string, status?: string) {
  // Update LED dashboard
  const ledId = agentToLedId[agent];
  if (ledId) {
    const ledContainer = document.getElementById(ledId);
    if (ledContainer) {
      const led = ledContainer.querySelector('.led');
      const actionText = ledContainer.querySelector('.led-action');

      if (led) {
        led.classList.remove('idle', 'active', 'waiting', 'error');
        if (status === 'error') {
          led.classList.add('error');
        } else if (status === 'waiting') {
          led.classList.add('waiting');
        } else if (status === 'complete') {
          led.classList.add('idle');
        } else {
          led.classList.add('active');
        }
      }

      if (actionText) {
        actionText.textContent = text.length > 20 ? text.substring(0, 18) + '...' : text;
      }
    }
  }

  // Also refresh file list if file was created
  if (text.toLowerCase().includes('created') || text.toLowerCase().includes('wrote')) {
    setTimeout(loadProjectFiles, 500);
  }
}

function resetAgents() {
  document.querySelectorAll('.agent-led').forEach(led => {
    const ledDot = led.querySelector('.led');
    const actionText = led.querySelector('.led-action');
    ledDot?.classList.remove('active', 'waiting', 'error');
    ledDot?.classList.add('idle');
    if (actionText) actionText.textContent = 'Idle';
  });
}

// === File Explorer ===
const fileTree = document.getElementById('file-tree');
const fileContent = document.getElementById('file-content');
const currentFileName = document.getElementById('current-file-name');
const refreshFilesBtn = document.getElementById('refresh-files-btn');
const closeFileBtn = document.getElementById('close-file-btn');

async function loadProjectFiles() {
  if (!fileTree) return;

  try {
    const response = await fetch(`${API_URL}/files`);
    const data = await response.json();

    if (data.files && data.files.length > 0) {
      fileTree.innerHTML = data.files.map((f: any) => `
        <div class="file-item" data-path="${f.path}" title="${f.path}">
          <i data-lucide="file-code"></i>
          <span>${f.name}</span>
        </div>
      `).join('');

      // Add click handlers
      fileTree.querySelectorAll('.file-item').forEach(item => {
        item.addEventListener('click', () => viewFile((item as HTMLElement).dataset.path || ''));
      });

      if (typeof lucide !== 'undefined') lucide.createIcons();
    } else {
      fileTree.innerHTML = '<div class="empty-state">No files yet...</div>';
    }
  } catch (error) {
    fileTree.innerHTML = '<div class="empty-state">Could not load files</div>';
  }
}

async function viewFile(path: string) {
  if (!fileContent || !currentFileName) return;

  try {
    const response = await fetch(`${API_URL}/files/${encodeURIComponent(path)}`);
    const data = await response.json();

    if (data.content) {
      currentFileName.textContent = path.split(/[\\/]/).pop() || path;
      fileContent.innerHTML = `<code>${escapeHtml(data.content)}</code>`;
      closeFileBtn?.classList.remove('hidden');
    } else {
      fileContent.innerHTML = `<code>Error: ${data.error}</code>`;
    }
  } catch (error) {
    fileContent.innerHTML = `<code>Error loading file</code>`;
  }
}

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

refreshFilesBtn?.addEventListener('click', loadProjectFiles);
closeFileBtn?.addEventListener('click', () => {
  if (currentFileName) currentFileName.textContent = 'No file selected';
  if (fileContent) fileContent.innerHTML = '<code>Select a file to view its contents...</code>';
  closeFileBtn?.classList.add('hidden');
});

// === Project Management ===
async function loadProjects() {
  try {
    const response = await fetch(`${API_URL}/projects`);
    const data = await response.json();
    renderProjects(data.projects);
    renderRecentProjects(data.projects.slice(0, 5));
  } catch (error) {
    console.error('Failed to load projects:', error);
  }
}

function renderProjects(projects: any[]) {
  if (!projectsGrid) return;

  if (projects.length === 0) {
    projectsGrid.innerHTML = '<div class="empty-state">No projects yet. Create one to get started!</div>';
    return;
  }

  projectsGrid.innerHTML = projects.map(p => `
        <div class="project-card" data-path="${p.path}">
            <div class="project-card-header">
              <h3>${p.name}</h3>
              <button class="delete-project-btn icon-btn" data-path="${p.path}" title="Delete project">
                <i data-lucide="trash-2"></i>
              </button>
            </div>
            <p class="objective">${p.objective || 'No objective set'}</p>
            <div class="meta">
                <span class="status-badge ${p.status}">${p.status.replace('_', ' ')}</span>
                <span>${formatDate(p.updated_at)}</span>
            </div>
        </div>
    `).join('');

  // Add click handlers for opening projects
  projectsGrid.querySelectorAll('.project-card').forEach(card => {
    card.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      // Don't open if clicking delete button
      if (!target.closest('.delete-project-btn')) {
        openProject(card.getAttribute('data-path') || '');
      }
    });
  });

  // Add delete handlers
  projectsGrid.querySelectorAll('.delete-project-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const path = (btn as HTMLElement).getAttribute('data-path');
      if (path && confirm('Are you sure you want to delete this project?')) {
        await deleteProject(path);
      }
    });
  });

  // Re-initialize icons
  if (typeof lucide !== 'undefined') lucide.createIcons();
}

async function deleteProject(path: string) {
  try {
    await fetch(`${API_URL}/projects/${encodeURIComponent(path)}`, {
      method: 'DELETE'
    });
    addLog('System', 'Project deleted');
    loadProjects();
  } catch (error) {
    addLog('System', `Error deleting project: ${error}`);
  }
}

function renderRecentProjects(projects: any[]) {
  if (!recentProjectsContainer) return;

  if (projects.length === 0) {
    recentProjectsContainer.innerHTML = '<div class="empty-state">No projects yet</div>';
    return;
  }

  recentProjectsContainer.innerHTML = projects.map(p => `
        <div class="project-item" data-path="${p.path}">
            <h4>${p.name}</h4>
            <p>${p.objective?.substring(0, 40) || 'No objective'}...</p>
        </div>
    `).join('');

  recentProjectsContainer.querySelectorAll('.project-item').forEach(item => {
    item.addEventListener('click', () => openProject(item.getAttribute('data-path') || ''));
  });
}

async function openProject(path: string) {
  try {
    const response = await fetch(`${API_URL}/projects/open?path=${encodeURIComponent(path)}`, {
      method: 'POST'
    });
    const data = await response.json();
    if (data.success) {
      projectNameInput.value = data.project.name;
      objectiveInput.value = data.project.objective || '';
      switchView('dashboard');
      addLog('System', `Opened project: ${data.project.name}`);
    }
  } catch (error) {
    console.error('Failed to open project:', error);
  }
}

function formatDate(isoString: string): string {
  if (!isoString || isoString === 'unknown') return 'Unknown';
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// === Orchestration ===
async function startOrchestration() {
  const objective = objectiveInput.value.trim();
  if (!objective) {
    addLog('System', 'Please enter an objective');
    return;
  }

  disableStartButton();

  try {
    const response = await fetch(`${API_URL}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        objective,
        project_name: projectNameInput.value.trim() || undefined
      })
    });

    const data = await response.json();
    currentProjectId = data.projectId;
    addLog('System', `Project started: ${data.projectId.substring(0, 8)}...`);
    loadProjects();
  } catch (error) {
    addLog('System', `Error: ${error}`);
    enableStartButton();
  }
}

function disableStartButton() {
  startBtn.disabled = true;
  startBtn.innerHTML = '<i data-lucide="loader-2"></i> Orchestrating...';
  if (typeof lucide !== 'undefined') lucide.createIcons();
}

function enableStartButton() {
  startBtn.disabled = false;
  startBtn.innerHTML = '<i data-lucide="play"></i> Start Orchestration';
  if (typeof lucide !== 'undefined') lucide.createIcons();
}

function sendGuidance() {
  const text = guidanceInput.value.trim();
  if (!text || !socket || !currentProjectId) return;

  socket.send(JSON.stringify({
    type: 'guidance',
    projectId: currentProjectId,
    text: text
  }));

  guidanceInput.value = '';
}

// === Modal ===
function showFinalOutput(text: string, _outputPath?: string) {
  const modal = document.getElementById('output-modal');
  const outputText = document.getElementById('output-text');

  if (modal && outputText) {
    outputText.textContent = text;
    modal.classList.remove('hidden');
  }
}

// === View Switching ===
function switchView(viewName: string) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

  const view = document.getElementById(`${viewName}-view`);
  const btn = document.querySelector(`.nav-btn[data-view="${viewName}"]`);

  if (view) view.classList.add('active');
  if (btn) btn.classList.add('active');

  if (viewName === 'projects') {
    loadProjects();
  } else if (viewName === 'agents') {
    const activeTab = document.querySelector('.log-tab.active');
    const agent = activeTab?.getAttribute('data-agent');
    if (agent) loadAgentLogs(agent);
  }
}

// === Agent Logs ===
async function loadAgentLogs(agent: string) {
  const viewer = document.getElementById('agent-log-viewer');
  if (!viewer) return;

  viewer.innerHTML = '<pre>Loading logs...</pre>';

  try {
    const response = await fetch(`${API_URL}/logs/${agent}`);
    const data = await response.json();
    viewer.innerHTML = `<pre>${data.logs}</pre>`;
  } catch (error) {
    viewer.innerHTML = `<pre>Error loading logs: ${error}</pre>`;
  }
}

// === Event Listeners ===
document.querySelectorAll('.log-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.log-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const agent = tab.getAttribute('data-agent');
    if (agent) loadAgentLogs(agent);
  });
});

document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const view = btn.getAttribute('data-view');
    if (view) switchView(view);
  });
});

startBtn?.addEventListener('click', startOrchestration);
guideBtn?.addEventListener('click', sendGuidance);

guidanceInput?.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') sendGuidance();
});

clearFeedBtn?.addEventListener('click', () => {
  logsContainer.innerHTML = '';
  addLog('System', 'Activity feed cleared');
});

document.getElementById('close-modal')?.addEventListener('click', () => {
  document.getElementById('output-modal')?.classList.add('hidden');
});

document.querySelector('.modal-backdrop')?.addEventListener('click', () => {
  document.getElementById('output-modal')?.classList.add('hidden');
});

document.getElementById('copy-output')?.addEventListener('click', () => {
  const text = document.getElementById('output-text')?.textContent || '';
  navigator.clipboard.writeText(text);
});

modelPresetSelect?.addEventListener('change', async () => {
  try {
    await fetch(`${API_URL}/models/preset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preset: modelPresetSelect.value })
    });
    addLog('System', `Model preset changed to: ${modelPresetSelect.value}`);
  } catch (error) {
    console.error('Failed to set model preset:', error);
  }
});

document.getElementById('new-project-btn')?.addEventListener('click', () => {
  projectNameInput.value = '';
  objectiveInput.value = '';
  switchView('dashboard');
});

// === Initialize ===
connectWS();
loadProjects();

// === Browse Folder for Existing Project ===
const browseFolderBtn = document.getElementById('browse-folder-btn');
const existingPathInput = document.getElementById('existing-path') as HTMLInputElement;
const importProjectBtn = document.getElementById('import-project-btn') as HTMLButtonElement;
const projectTypeInfo = document.getElementById('project-type-info');
const detectedFramework = document.getElementById('detected-framework');
const detectedLanguage = document.getElementById('detected-language');

// Check if pywebview API is available (desktop app mode)
declare const pywebview: { api: { select_folder: () => Promise<string | null> } } | undefined;

browseFolderBtn?.addEventListener('click', async () => {
  try {
    let folderPath: string | null = null;

    // Try pywebview API first (desktop app)
    if (typeof pywebview !== 'undefined' && pywebview.api) {
      folderPath = await pywebview.api.select_folder();
    } else {
      // Fallback: prompt for path (web mode)
      folderPath = prompt('Enter the full path to your project folder:');
    }

    if (folderPath && existingPathInput) {
      existingPathInput.value = folderPath;

      // Analyze the project
      try {
        const response = await fetch(`${API_URL}/projects/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: folderPath })
        });

        const data = await response.json();
        if (data.success && data.project_type) {
          // Show project type info
          if (projectTypeInfo) projectTypeInfo.classList.remove('hidden');
          if (detectedFramework) detectedFramework.textContent = data.project_type.framework || 'Unknown';
          if (detectedLanguage) detectedLanguage.textContent = data.project_type.language || 'Unknown';
          if (importProjectBtn) importProjectBtn.disabled = false;

          // Re-initialize icons
          if (typeof lucide !== 'undefined') lucide.createIcons();
        } else {
          addLog('System', `Could not analyze project: ${data.error || 'Unknown error'}`);
          if (importProjectBtn) importProjectBtn.disabled = true;
        }
      } catch (error) {
        addLog('System', `Error analyzing project: ${error}`);
      }
    }
  } catch (error) {
    addLog('System', `Error selecting folder: ${error}`);
  }
});

importProjectBtn?.addEventListener('click', async () => {
  const path = existingPathInput?.value;
  if (!path) return;

  importProjectBtn.disabled = true;
  importProjectBtn.innerHTML = '<i data-lucide="loader-2"></i> Importing...';
  if (typeof lucide !== 'undefined') lucide.createIcons();

  try {
    const response = await fetch(`${API_URL}/projects/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: path,
        name: projectNameInput?.value || undefined
      })
    });

    const data = await response.json();
    if (data.success) {
      addLog('System', `Imported project: ${data.name} (${data.project_type?.framework || 'Unknown'})`);

      // Update UI
      if (projectNameInput) projectNameInput.value = data.name;

      // Clear import section
      if (existingPathInput) existingPathInput.value = '';
      if (projectTypeInfo) projectTypeInfo.classList.add('hidden');

      loadProjects();
    } else {
      addLog('System', `Failed to import: ${data.error}`);
    }
  } catch (error) {
    addLog('System', `Error importing project: ${error}`);
    importProjectBtn.disabled = false;
    importProjectBtn.innerHTML = '<i data-lucide="file-input"></i> Import & Continue Working';
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }
});

// === Ollama Management ===
const ollamaStatusDot = document.getElementById('ollama-status-dot');
const ollamaStatusText = document.getElementById('ollama-status-text');
const refreshOllamaBtn = document.getElementById('refresh-ollama-btn');
const startOllamaBtn = document.getElementById('start-ollama-btn') as HTMLButtonElement | null;
const modelList = document.getElementById('model-list');
const downloadModelBtn = document.getElementById('download-model-btn') as HTMLButtonElement | null;
const modelToDownload = document.getElementById('model-to-download') as HTMLSelectElement;
const downloadProgress = document.getElementById('download-progress');
const downloadStatus = document.getElementById('download-status');

async function checkOllamaStatus() {
  if (!ollamaStatusDot || !ollamaStatusText) return;

  ollamaStatusText.textContent = 'Checking...';

  try {
    const response = await fetch(`${API_URL}/ollama/status`);
    const data = await response.json();

    if (data.online) {
      ollamaStatusDot.classList.add('online');
      ollamaStatusDot.classList.remove('offline');
      ollamaStatusText.textContent = 'Running';
      if (startOllamaBtn) startOllamaBtn.classList.add('hidden');
      loadOllamaModels();
    } else {
      ollamaStatusDot.classList.add('offline');
      ollamaStatusDot.classList.remove('online');
      ollamaStatusText.textContent = 'Not Running';
      if (startOllamaBtn) startOllamaBtn.classList.remove('hidden');
      if (modelList) modelList.innerHTML = '<div class="empty-state">Start Ollama to see models</div>';
    }
  } catch (error) {
    ollamaStatusDot.classList.add('offline');
    ollamaStatusDot.classList.remove('online');
    ollamaStatusText.textContent = 'Error';
  }
}

async function loadOllamaModels() {
  if (!modelList) return;

  try {
    const response = await fetch(`${API_URL}/ollama/models`);
    const data = await response.json();

    if (data.success && data.models.length > 0) {
      modelList.innerHTML = data.models.map((m: any) => `
        <div class="model-item">
          <div class="model-info">
            <span class="model-name">${m.name}</span>
            <span class="model-size">${formatBytes(m.size)}</span>
          </div>
        </div>
      `).join('');
    } else {
      modelList.innerHTML = '<div class="empty-state">No models downloaded yet</div>';
    }
  } catch (error) {
    modelList.innerHTML = '<div class="empty-state">Failed to load models</div>';
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

refreshOllamaBtn?.addEventListener('click', checkOllamaStatus);

startOllamaBtn?.addEventListener('click', async () => {
  try {
    const response = await fetch(`${API_URL}/ollama/start`, { method: 'POST' });
    const data = await response.json();

    if (data.success) {
      addLog('System', 'Ollama server starting...');
      setTimeout(checkOllamaStatus, 2000);
    } else {
      addLog('System', `Failed to start Ollama: ${data.error}`);
    }
  } catch (error) {
    addLog('System', `Error starting Ollama: ${error}`);
  }
});

downloadModelBtn?.addEventListener('click', async () => {
  const modelName = modelToDownload?.value;
  if (!modelName) return;

  if (downloadProgress) downloadProgress.classList.remove('hidden');
  if (downloadStatus) downloadStatus.textContent = `Downloading ${modelName}...`;
  if (downloadModelBtn) downloadModelBtn.disabled = true;

  try {
    const response = await fetch(`${API_URL}/ollama/pull`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: modelName })
    });

    const data = await response.json();

    if (data.success) {
      addLog('System', `Started downloading ${modelName}. This may take a while.`);
      if (downloadStatus) downloadStatus.textContent = 'Download started in background...';

      // Poll for completion
      const checkInterval = setInterval(async () => {
        await loadOllamaModels();
        const models = modelList?.querySelectorAll('.model-name');
        const downloaded = Array.from(models || []).some((m: any) => m.textContent?.includes(modelName.split(':')[0]));
        if (downloaded) {
          clearInterval(checkInterval);
          if (downloadProgress) downloadProgress.classList.add('hidden');
          addLog('System', `Model ${modelName} downloaded successfully!`);
        }
      }, 5000);

      setTimeout(() => clearInterval(checkInterval), 300000); // Stop after 5 min
    } else {
      addLog('System', `Failed to download: ${data.error}`);
      if (downloadProgress) downloadProgress.classList.add('hidden');
    }
  } catch (error) {
    addLog('System', `Error downloading model: ${error}`);
    if (downloadProgress) downloadProgress.classList.add('hidden');
  } finally {
    if (downloadModelBtn) downloadModelBtn.disabled = false;
  }
});

// Check Ollama status on page load
setTimeout(checkOllamaStatus, 1000);

// === Model Backup ===
const ollamaModelsPath = document.getElementById('ollama-models-path') as HTMLInputElement;
const copyPathBtn = document.getElementById('copy-path-btn');
const openModelsFolderBtn = document.getElementById('open-models-folder-btn');

// Load Ollama models path
async function loadOllamaModelsPath() {
  try {
    const response = await fetch(`${API_URL}/ollama/models-path`);
    const data = await response.json();
    if (data.path && ollamaModelsPath) {
      ollamaModelsPath.value = data.path;
    }
  } catch (error) {
    console.log('Could not load models path');
  }
}

copyPathBtn?.addEventListener('click', () => {
  const path = ollamaModelsPath?.value;
  if (path) {
    navigator.clipboard.writeText(path);
    addLog('System', 'Models path copied to clipboard');
  }
});

openModelsFolderBtn?.addEventListener('click', async () => {
  try {
    await fetch(`${API_URL}/ollama/open-models-folder`, { method: 'POST' });
  } catch (error) {
    addLog('System', `Could not open folder: ${error}`);
  }
});

setTimeout(loadOllamaModelsPath, 1500);

// === No-Cost Free API Management ===
const nocostStatusDot = document.getElementById('nocost-status-dot');
const nocostStatusText = document.getElementById('nocost-status-text');
const refreshNocostBtn = document.getElementById('refresh-nocost-btn');
const nocostModelList = document.getElementById('nocost-model-list');

async function checkNocostStatus() {
  if (!nocostStatusDot || !nocostStatusText) return;

  nocostStatusText.textContent = 'Checking...';

  try {
    const response = await fetch(`${API_URL}/nocost/status`);
    const data = await response.json();

    if (data.online) {
      nocostStatusDot.classList.add('online');
      nocostStatusDot.classList.remove('offline');
      nocostStatusText.textContent = 'Available';
      loadNocostModels();
    } else {
      nocostStatusDot.classList.add('offline');
      nocostStatusDot.classList.remove('online');
      nocostStatusText.textContent = 'Not Available';
      // Still show static models from config
      loadNocostModels();
    }
  } catch (error) {
    nocostStatusDot.classList.add('offline');
    nocostStatusDot.classList.remove('online');
    nocostStatusText.textContent = 'Error';
    // Still try to load models from config fallback
    loadNocostModels();
  }
}

async function loadNocostModels() {
  if (!nocostModelList) return;

  try {
    const response = await fetch(`${API_URL}/nocost/models`);
    const data = await response.json();

    if (data.success && data.models.length > 0) {
      nocostModelList.innerHTML = data.models.map((m: any) => `
        <div class="model-item">
          <div class="model-info">
            <span class="model-name">${m.name}</span>
            ${m.size > 0 ? `<span class="model-size">${formatBytes(m.size)}</span>` : '<span class="model-size free-badge">Free</span>'}
          </div>
        </div>
      `).join('');
    } else {
      nocostModelList.innerHTML = '<div class="empty-state">No free models available</div>';
    }
  } catch (error) {
    nocostModelList.innerHTML = '<div class="empty-state">Failed to load free models</div>';
  }
}

refreshNocostBtn?.addEventListener('click', checkNocostStatus);

// Check no-cost API status on page load (after Ollama check)
setTimeout(checkNocostStatus, 2000);
