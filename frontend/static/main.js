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
        const res = await fetch(`${API_BASE}${endpoint}`);
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
        alert(result.message || 'Mission launched!');
        loadGoals();
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
        const activeGoals = goals.filter(g => g.status === 'running' || g.status === 'active').length;
        const completedGoals = goals.filter(g => g.status === 'completed').length;

        // Extract latest success rate from metrics
        const successMetric = metrics.find(m => m.metric_name === 'success_rate');
        const successRate = successMetric ? (successMetric.value * 100).toFixed(0) : '--';

        container.innerHTML = `
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Total Goals</span></div>
                <div class="card-value">${totalGoals}</div>
            </div>
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Active Missions</span></div>
                <div class="card-value success">${activeGoals}</div>
            </div>
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Completed</span></div>
                <div class="card-value">${completedGoals}</div>
            </div>
            <div class="card fade-in">
                <div class="card-header"><span class="card-title">Success Rate</span></div>
                <div class="card-value success">${successRate}%</div>
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

// ── Plans / Mission ─────────────────────────

async function loadMission() {
    const params = new URLSearchParams(window.location.search);
    const goalId = params.get('goal_id');

    if (!goalId) {
        document.getElementById('mission-content').innerHTML = `
            <div class="empty-state">
                <div class="icon">📋</div>
                <p>Select a goal from the dashboard to view its mission.</p>
            </div>
        `;
        return;
    }

    try {
        const [goal, plans] = await Promise.all([
            api.get(`/goals/${goalId}`),
            api.get(`/plans/${goalId}`),
        ]);

        document.getElementById('mission-title').textContent = goal.title;
        document.getElementById('mission-status').className = `badge badge-${goal.status}`;
        document.getElementById('mission-status').textContent = goal.status;

        const plansContainer = document.getElementById('plans-list');
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

document.addEventListener('DOMContentLoaded', () => {
    setActiveNav();
    loadGoals();
    loadMetrics();
    loadTools();
    loadMission();
});
