const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

let socket: WebSocket | null = null;
let currentProjectId: string | null = null;

// DOM Elements
const backendStatus = document.getElementById('backend-status');
const objectiveInput = document.getElementById('objective-input') as HTMLTextAreaElement;
const startBtn = document.getElementById('start-btn') as HTMLButtonElement;
const guidanceInput = document.getElementById('guidance-input') as HTMLInputElement;
const guideBtn = document.getElementById('guide-btn') as HTMLButtonElement;
const logsContainer = document.getElementById('logs-container') as HTMLDivElement;
const clearFeedBtn = document.getElementById('clear-feed');

const agentCards = {
  Orchestrator: document.getElementById('agent-orchestrator'),
  'UI/UX Designer': document.getElementById('agent-uiux'),
  'Developer': document.getElementById('agent-dev'),
  'QA Tester': document.getElementById('agent-qa')
};

function connectWS() {
  socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    backendStatus?.classList.add('online');
    if (backendStatus) backendStatus.innerHTML = '<span class="dot"></span> Backend Online';
    addLog('System', 'Connected to backend server.');
  };

  socket.onclose = () => {
    backendStatus?.classList.remove('online');
    if (backendStatus) backendStatus.innerHTML = '<span class="dot"></span> Backend Offline';
    addLog('System', 'Disconnected from backend server. Retrying...');
    setTimeout(connectWS, 3000);
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleSocketMessage(data);
  };
}

function handleSocketMessage(data: any) {
  switch (data.type) {
    case 'log':
      addLog(data.agent, data.text, data.status);
      updateAgentStatus(data.agent, data.text, data.status);
      break;
    case 'final_output':
      showFinalOutput(data.text);
      resetAgents();
      break;
  }
}

function addLog(agent: string, text: string, status?: string) {
  const entry = document.createElement('div');
  entry.className = `log-entry ${agent.toLowerCase().replace('/', '').split(' ')[0]}`;

  const label = document.createElement('span');
  label.className = 'log-label';
  label.textContent = agent;

  const content = document.createElement('div');
  content.textContent = text;

  entry.appendChild(label);
  entry.appendChild(content);
  logsContainer.prepend(entry);
}

function updateAgentStatus(agent: string, text: string, status?: string) {
  // Reset all cards first
  Object.values(agentCards).forEach(card => card?.classList.remove('active'));

  const card = (agentCards as any)[agent];
  if (card) {
    card.classList.add('active');
    const statusEl = card.querySelector('.agent-status');
    if (statusEl) statusEl.textContent = text.length > 30 ? text.substring(0, 27) + "..." : text;
  }
}

function resetAgents() {
  Object.entries(agentCards).forEach(([name, card]) => {
    card?.classList.remove('active');
    const statusEl = card?.querySelector('.agent-status');
    if (statusEl) statusEl.textContent = 'Idle';
  });
}

async function startOrchestration() {
  const objective = objectiveInput.value.trim();
  if (!objective) return;

  startBtn.disabled = true;
  startBtn.textContent = 'Orchestrating...';

  try {
    const response = await fetch(`${API_URL}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ objective })
    });

    const data = await response.json();
    currentProjectId = data.projectId;
    addLog('System', `Started project: ${currentProjectId}`);
  } catch (error) {
    addLog('System', `Error starting project: ${error}`);
    startBtn.disabled = false;
    startBtn.textContent = 'Start Orchestration';
  }
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

function showFinalOutput(text: string) {
  const modal = document.getElementById('final-output-modal');
  const outputText = document.getElementById('final-output-text');
  if (modal && outputText) {
    outputText.textContent = text; // In a real app, use a markdown renderer
    modal.classList.remove('hidden');
  }
  startBtn.disabled = false;
  startBtn.textContent = 'Start Orchestration';
}

// Event Listeners
startBtn.addEventListener('click', startOrchestration);
guideBtn.addEventListener('click', sendGuidance);
clearFeedBtn?.addEventListener('click', () => {
  logsContainer.innerHTML = '';
});
document.getElementById('close-modal')?.addEventListener('click', () => {
  document.getElementById('final-output-modal')?.classList.add('hidden');
});

// Initial Connection
connectWS();
