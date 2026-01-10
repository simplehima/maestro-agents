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

const agentCards: Record<string, HTMLElement | null> = {
  'Orchestrator': document.getElementById('agent-orchestrator'),
  'Research': document.getElementById('agent-research'),
  'UI/UX Designer': document.getElementById('agent-uiux'),
  'Developer': document.getElementById('agent-dev'),
  'Security': document.getElementById('agent-security'),
  'QA Tester': document.getElementById('agent-qa'),
  'Documentation': document.getElementById('agent-docs'),
  'Refiner': document.getElementById('agent-refiner')
};

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

function updateAgentStatus(agent: string, text: string, _status?: string) {
  Object.values(agentCards).forEach(card => card?.classList.remove('active'));

  const card = agentCards[agent];
  if (card) {
    card.classList.add('active');
    const statusEl = card.querySelector('.agent-status');
    if (statusEl) {
      statusEl.textContent = text.length > 25 ? text.substring(0, 22) + '...' : text;
      statusEl.classList.add('active');
    }
  }
}

function resetAgents() {
  Object.entries(agentCards).forEach(([, card]) => {
    card?.classList.remove('active');
    const statusEl = card?.querySelector('.agent-status');
    if (statusEl) {
      statusEl.textContent = 'Idle';
      statusEl.classList.remove('active');
    }
  });
}

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
            <h3>${p.name}</h3>
            <p class="objective">${p.objective || 'No objective set'}</p>
            <div class="meta">
                <span class="status-badge ${p.status}">${p.status.replace('_', ' ')}</span>
                <span>${formatDate(p.updated_at)}</span>
            </div>
        </div>
    `).join('');

  // Add click handlers
  projectsGrid.querySelectorAll('.project-card').forEach(card => {
    card.addEventListener('click', () => openProject(card.getAttribute('data-path') || ''));
  });
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
