/**
 * AEGIS — Frontend JavaScript Module
 *
 * Vanilla JS for API calls, DOM updates, and navigation.
 * No framework dependencies.
 */

const API_BASE = '/api';

// ── API Client ─────────────────────────────

const api = {
    async get(endpoint) {
        // Add cache-busting parameter to prevent stale polling data
        const separator = endpoint.includes('?') ? '&' : '?';
        const res = await fetch(`${API_BASE}${endpoint}${separator}_t=${Date.now()}`);
        if (!res.ok) throw new Error(`GET ${endpoint} failed: ${res.status}`);
        return res.json();
    },

    async post(endpoint, data) {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error(`POST ${endpoint} failed: ${res.status}`);
        return res.json();
    },
};

// ── Goals ───────────────────────────────────

async function loadGoals() {
    const container = document.getElementById('goals-list');
    if (!container) return;

    try {
        const goals = await api.get('/goals');
        if (goals.length === 0) {
            container.innerHTML = `
                <div class="empty-state fade-in">
                    <div class="icon">🎯</div>
                    <p>No goals yet. Create your first goal to get started.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = goals.map(goal => `
            <tr class="fade-in">
                <td><strong>${escapeHtml(goal.title)}</strong></td>
                <td><span class="badge badge-${goal.status}">${goal.status}</span></td>
                <td>${formatDate(goal.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="launchMission('${goal.id}')">
                        ▶ Launch
                    </button>
                    <a href="/mission?goal_id=${goal.id}" class="btn btn-sm btn-secondary">
                        View
                    </a>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        container.innerHTML = `<tr><td colspan="4">Failed to load goals: ${err.message}</td></tr>`;
    }
}

async function createGoal(event) {
    event.preventDefault();
    const form = event.target;
    const data = {
        title: form.querySelector('#goal-title').value,
        description: form.querySelector('#goal-description').value,
        schedule: form.querySelector('#goal-schedule')?.value || null,
    };

    // Include skill_id if set by autofill
    const skillIdField = form.querySelector('#goal-skill-id');
    if (skillIdField && skillIdField.value) {
        data.skill_id = skillIdField.value;
    }

    try {
        await api.post('/goals', data);
        form.reset();
        closeModal('create-goal-modal');
        loadGoals();
        loadMetrics();
    } catch (err) {
        alert('Failed to create goal: ' + err.message);
    }
}

async function launchMission(goalId) {
    try {
        const result = await api.post(`/goals/${goalId}/launch`, {});
        // Auto-redirect to mission page so user sees live polling
        window.location.href = `/mission?goal_id=${goalId}`;
    } catch (err) {
        alert('Failed to launch: ' + err.message);
    }
}

// ── Metrics ─────────────────────────────────

async function loadMetrics() {
    const container = document.getElementById('metrics-cards');
    if (!container) return;

    try {
        const goals = await api.get('/goals');
        const metrics = await api.get('/metrics');

        const totalGoals = goals.length;
        const activeGoals = goals.filter(g => g.status === 'running').length;
        const completedGoals = goals.filter(g => g.status === 'completed').length;
        const failedGoals = goals.filter(g => g.status === 'failed').length;
        const pendingGoals = goals.filter(g => g.status === 'pending').length;

        // Calculate success rate from completed/total finished
        const finishedGoals = completedGoals + failedGoals;
        const successRate = finishedGoals > 0
            ? ((completedGoals / finishedGoals) * 100).toFixed(0)
            : '--';

        // Aggregate latency from all runs
        const allLatencies = metrics.filter(m => m.metric_name === 'avg_latency_s');
        const avgLatency = allLatencies.length > 0
            ? (allLatencies.reduce((sum, m) => sum + m.value, 0) / allLatencies.length).toFixed(2)
            : null;

        // Total tools from DB
        const toolsMetrics = metrics.filter(m => m.metric_name === 'tools_generated');
        const totalTools = toolsMetrics.length > 0
            ? toolsMetrics.reduce((sum, m) => sum + m.value, 0)
            : 0;

        // Total tasks executed
        const taskMetrics = metrics.filter(m => m.metric_name === 'tasks_executed');
        const totalTasks = taskMetrics.length > 0
            ? taskMetrics.reduce((sum, m) => sum + m.value, 0)
            : 0;

        container.innerHTML = `
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Total Goals</span></div>
                <div class="card-value">${totalGoals}</div>
                <div style="font-size:0.7rem;color:var(--oat-fg-alt);margin-top:0.25rem">
                    ${pendingGoals} pending · ${activeGoals} active
                </div>
            </div>
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Completed</span></div>
                <div class="card-value success">${completedGoals}</div>
            </div>
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Failed</span></div>
                <div class="card-value" style="color: var(--aegis-error, #ef4444)">${failedGoals}</div>
            </div>
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Success Rate</span></div>
                <div class="card-value success">${successRate}%</div>
            </div>
            ${avgLatency ? `
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Avg Latency</span></div>
                <div class="card-value">${avgLatency}s</div>
            </div>` : ''}
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Tasks Run</span></div>
                <div class="card-value">${totalTasks.toFixed(0)}</div>
            </div>
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Tools Generated</span></div>
                <div class="card-value">${totalTools.toFixed(0)}</div>
            </div>
        `;
    } catch (err) {
        console.error('Failed to load metrics:', err);
    }
}

// ── Tools ───────────────────────────────────

async function loadTools() {
    const container = document.getElementById('tools-list');
    if (!container) return;

    try {
        const tools = await api.get('/tools');
        if (tools.length === 0) {
            container.innerHTML = `
                <div class="empty-state fade-in">
                    <div class="icon">🔧</div>
                    <p>No tools registered yet. Tools are auto-generated during missions.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = tools.map(tool => `
            <tr class="fade-in">
                <td><strong>${escapeHtml(tool.name)}</strong></td>
                <td>${escapeHtml(tool.description)}</td>
                <td>${(tool.trust_score * 100).toFixed(0)}%</td>
                <td>${formatDate(tool.created_at)}</td>
            </tr>
        `).join('');
    } catch (err) {
        container.innerHTML = `<tr><td colspan="4">Failed to load tools: ${err.message}</td></tr>`;
    }
}

let missionPollTimer = null;

async function loadMission() {
    const params = new URLSearchParams(window.location.search);
    const goalId = params.get('goal_id');

    if (!goalId) {
        const content = document.getElementById('mission-content');
        if (content) {
            content.innerHTML = `
                <div class="empty-state">
                    <div class="icon">📋</div>
                    <p>Select a goal from the dashboard to view its mission.</p>
                </div>
            `;
        }
        return;
    }

    try {
        const data = await api.get(`/missions/${goalId}/status`);
        const { goal, plans, tasks, runs } = data;

        const titleEl = document.getElementById('mission-title');
        const statusEl = document.getElementById('mission-status');
        if (titleEl) titleEl.textContent = goal.title;
        if (statusEl) {
            statusEl.className = `badge badge-${goal.status}`;
            statusEl.textContent = goal.status;
        }

        // Render plans
        const plansContainer = document.getElementById('plans-list');
        if (plansContainer) {
            if (plans.length === 0) {
                plansContainer.innerHTML = '<p class="empty-state">No plans generated yet.</p>';
            } else {
                plansContainer.innerHTML = plans.map(plan => `
                    <div class="card fade-in">
                        <div class="card-header">
                            <span class="card-title">Plan</span>
                            <span class="badge badge-${plan.score > 0.5 ? 'completed' : 'pending'}">
                                Score: ${(plan.score * 100).toFixed(0)}%
                            </span>
                        </div>
                        <div class="plan-steps">
                            ${(plan.plan_json.steps || []).map((step, i) => `
                                <div class="log-line">${i + 1}. ${escapeHtml(step.name || 'Unnamed step')}</div>
                            `).join('')}
                        </div>
                    </div>
                `).join('');
            }
        }

        // Render tasks
        const tasksContainer = document.getElementById('tasks-list');
        if (tasksContainer) {
            if (tasks.length === 0) {
                tasksContainer.innerHTML = '<tr><td colspan="4" class="empty-state">No tasks yet.</td></tr>';
            } else {
                tasksContainer.innerHTML = tasks.map(task => `
                    <tr class="fade-in">
                        <td><strong>${escapeHtml(task.name)}</strong></td>
                        <td>${escapeHtml(task.assigned_agent || '—')}</td>
                        <td><span class="badge badge-${task.status}">${task.status}</span></td>
                        <td>${task.retries}</td>
                    </tr>
                `).join('');
            }
        }

        // Render logs from runs
        const logPanel = document.getElementById('log-panel');
        if (logPanel && runs.length > 0) {
            logPanel.innerHTML = runs.map(run => `
                <div class="log-line ${run.success ? 'success' : 'error'}">
                    ${escapeHtml(run.logs || 'No output')}
                </div>
            `).join('');
            logPanel.scrollTop = logPanel.scrollHeight;
        } else if (logPanel) {
            logPanel.innerHTML = '<div class="log-line info">No execution logs yet.</div>';
        }

        // Auto-poll while mission is running or just launched
        if (goal.status === 'running' || goal.status === 'pending') {
            if (!missionPollTimer) {
                missionPollTimer = setInterval(() => loadMission(), 3000);
            }
        } else {
            // Mission finished — stop polling
            if (missionPollTimer) {
                clearInterval(missionPollTimer);
                missionPollTimer = null;
            }
        }

    } catch (err) {
        console.error('Failed to load mission:', err);
    }
}

// ── WebSocket Logs ──────────────────────────

function connectLogs(taskId) {
    const panel = document.getElementById('log-panel');
    if (!panel) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/logs/${taskId}`);

    ws.onmessage = (event) => {
        const line = document.createElement('div');
        line.className = 'log-line info';
        line.textContent = event.data;
        panel.appendChild(line);
        panel.scrollTop = panel.scrollHeight;
    };

    ws.onerror = () => {
        const line = document.createElement('div');
        line.className = 'log-line error';
        line.textContent = '[Connection error]';
        panel.appendChild(line);
    };

    return ws;
}

// ── Modal Helpers ───────────────────────────

function openModal(id) {
    document.getElementById(id)?.classList.add('open');
}

function closeModal(id) {
    document.getElementById(id)?.classList.remove('open');
}

// ── Utilities ───────────────────────────────

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
    });
}

// ── Navigation Active State ─────────────────

function setActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.sidebar nav a').forEach(link => {
        link.classList.toggle('active', link.getAttribute('href') === path);
    });
}

// ── Init ────────────────────────────────────

let dashboardPollTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    setActiveNav();
    loadGoals();
    loadMetrics();
    loadTools();
    loadMission();

    // Auto-refresh dashboard while goals are running
    const isDashboard = window.location.pathname === '/';
    if (isDashboard) {
        dashboardPollTimer = setInterval(async () => {
            try {
                const goals = await api.get('/goals');
                const hasRunning = goals.some(g => g.status === 'running');
                if (hasRunning) {
                    loadGoals();
                    loadMetrics();
                } else if (dashboardPollTimer) {
                    // No running goals, stop polling
                    clearInterval(dashboardPollTimer);
                    dashboardPollTimer = null;
                }
            } catch (e) { /* ignore */ }
        }, 5000);
    }

    // Handle autofill from Skill Browser preview
    const params = new URLSearchParams(window.location.search);
    if (params.get('autofill') === '1') {
        const titleInput = document.getElementById('goal-title');
        const descInput = document.getElementById('goal-description');

        if (titleInput) titleInput.value = params.get('title') || '';
        if (descInput) descInput.value = params.get('description') || '';

        // Set skill_id in hidden field
        const skillId = params.get('skill_id');
        if (skillId) {
            let hiddenField = document.getElementById('goal-skill-id');
            if (!hiddenField) {
                // Create hidden input dynamically
                hiddenField = document.createElement('input');
                hiddenField.type = 'hidden';
                hiddenField.id = 'goal-skill-id';
                hiddenField.name = 'skill_id';
                const form = document.querySelector('#create-goal-modal form');
                if (form) form.appendChild(hiddenField);
            }
            hiddenField.value = skillId;
        }

        openModal('create-goal-modal');

        // Clean URL
        window.history.replaceState({}, '', '/');
    }
});
