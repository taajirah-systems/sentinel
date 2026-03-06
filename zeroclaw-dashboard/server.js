/**
 * ZeroClaw Dashboard — API Bridge Server
 * Runs on port 4301. The Angular dev proxy routes /api/* here.
 * Serves live data from: system, openclaw.json, tasks.json, sentinel logs.
 */

const http = require('http');
const { spawn, execSync } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

const PORT = 4301;
const LOG_FILE = '/tmp/zeroclaw.stdout.log';
const TASKS_FILE = path.join(__dirname, 'data', 'tasks.json');
const OPENCLAW_RC = path.join(os.homedir(), '.openclaw', 'openclaw.json');
const SENTINEL_DIR = path.join(__dirname, '..');
const LEDGER_FILE = path.join(SENTINEL_DIR, 'data', 'ledger.jsonl');
const PEOPLE_FILE = path.join(__dirname, 'data', 'people.json');
const AUTH_REQUESTS_FILE = path.join(__dirname, 'data', 'auth-requests.json');
const PIPELINES_FILE = path.join(__dirname, 'data', 'pipelines.json');
const WORKSPACES_FILE = path.join(__dirname, 'data', 'workspaces.json');
const RADAR_FILE = path.join(__dirname, 'data', 'radar.json');

// ─── Helpers ────────────────────────────────────────────────────────────────

function readJSON(filePath, fallback = []) {
    try {
        if (fs.existsSync(filePath)) {
            return JSON.parse(fs.readFileSync(filePath, 'utf8'));
        }
    } catch (e) {
        console.error(`[server] Failed to read ${filePath}:`, e.message);
    }
    return fallback;
}

function jsonResponse(res, data, status = 200) {
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(data));
}

function parseBody(req) {
    return new Promise((resolve, reject) => {
        let body = '';
        req.on('data', chunk => body += chunk.toString());
        req.on('end', () => {
            try { resolve(JSON.parse(body)); }
            catch (e) { resolve({}); }
        });
        req.on('error', reject);
    });
}

/** Get live system metrics via Node.js os module */
function getSystemMetrics() {
    const cpus = os.cpus();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const usedMem = totalMem - freeMem;

    // Get disk usage for root
    let disk = '—';
    try {
        const dfOut = execSync("df -h / | tail -1 | awk '{print $3\"/\"$2}'", { timeout: 2000 }).toString().trim();
        disk = dfOut;
    } catch (_) { }

    // Network stats (best effort)
    let netIn = '—', netOut = '—';
    try {
        const netInterfaces = os.networkInterfaces();
        // Just show interface count as a proxy
        const ifaceCount = Object.keys(netInterfaces).length;
        netIn = `${ifaceCount} interfaces`;
        netOut = `${ifaceCount} interfaces`;
    } catch (_) { }

    // CPU usage: average idle vs total across all cores
    let cpuPercent = '—';
    try {
        const loads = os.loadavg();
        const cpuCount = cpus.length;
        cpuPercent = `${Math.min(100, (loads[0] / cpuCount * 100)).toFixed(1)}%`;
    } catch (_) { }

    // Uptime
    const uptimeSec = os.uptime();
    const days = Math.floor(uptimeSec / 86400);
    const hours = Math.floor((uptimeSec % 86400) / 3600);
    const mins = Math.floor((uptimeSec % 3600) / 60);
    const uptimeStr = `${days}d ${hours}h ${mins}m`;

    const memGB = (usedMem / 1e9).toFixed(1);
    const totalGB = (totalMem / 1e9).toFixed(1);

    return {
        cpu: cpuPercent,
        memory: `${memGB} GB / ${totalGB} GB`,
        disk,
        network_in: '—',
        network_out: '—',
        uptime: uptimeStr
    };
}

/** Get running processes from ps (macOS-compatible) */
function getProcesses() {
    try {
        const out = execSync(
            "ps -ax -o pid,pcpu,rss,stat,comm | sort -k2 -rn | head -20",
            { timeout: 3000 }
        ).toString().trim();
        const lines = out.split('\n').slice(1); // skip header
        return lines.map(line => {
            const parts = line.trim().split(/\s+/);
            const pid = parts[0] || '';
            const cpu = parseFloat(parts[1] || '0');
            const memKB = parseInt(parts[2] || '0', 10);
            const stat = parts[3] || '';
            const name = parts.slice(4).join(' ').split('/').pop(); // basename
            const status = stat.startsWith('S') ? 'sleeping' :
                stat.startsWith('Z') ? 'zombie' :
                    stat.startsWith('R') ? 'running' : 'running';
            return { name, pid, cpu, memory: `${(memKB / 1024).toFixed(0)} MB`, status };
        }).filter(p => p.name && p.pid);
    } catch (e) {
        console.error('[server] getProcesses error:', e.message);
        return [];
    }
}

/** Read ledger from JSONL file */
function getLedger() {
    try {
        if (fs.existsSync(LEDGER_FILE)) {
            return fs.readFileSync(LEDGER_FILE, 'utf8')
                .split('\n')
                .filter(l => l.trim())
                .map(l => JSON.parse(l));
        }
    } catch (e) {
        console.error('[server] getLedger error:', e.message);
    }
    return [];
}

/** Read agents from openclaw.json, cross-reference tasks.json for active task counts */
function getAgents() {
    try {
        if (fs.existsSync(OPENCLAW_RC)) {
            const config = JSON.parse(fs.readFileSync(OPENCLAW_RC, 'utf8'));
            const agentList = config.agents?.list || [];
            const primaryModel = config.agents?.defaults?.model?.primary || 'unknown';

            // Cross-reference tasks to compute tasksActive per agent
            const tasks = readJSON(TASKS_FILE, []);
            const activeTasks = tasks.filter(t =>
                t.status === 'in_progress' || t.status === 'inProgress'
            );

            return agentList.map(agent => {
                const agentName = (agent.name || '').toLowerCase();
                const count = activeTasks.filter(t => {
                    const assignee = (t.assignee || t.agent || '').toLowerCase();
                    return assignee && agentName && assignee.includes(agentName.split(' ')[0]);
                }).length;
                return {
                    id: agent.id,
                    name: agent.name,
                    status: 'Online',
                    model: primaryModel,
                    tasksActive: count
                };
            });
        }
    } catch (e) {
        console.error('[server] getAgents error:', e.message);
    }
    return [];
}

// ─── Server ─────────────────────────────────────────────────────────────────

const server = http.createServer(async (req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

    const url = req.url.split('?')[0]; // strip query string

    // ── GET /api/logs (SSE) ──────────────────────────────────────────────────
    if (url === '/api/logs') {
        res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        });
        res.write(`data: ${JSON.stringify({ source: 'system', message: 'Connected to ZeroClaw log stream', timestamp: new Date().toISOString() })}\n\n`);

        const logPath = fs.existsSync(LOG_FILE) ? LOG_FILE : '/tmp/sentinel.log';
        if (!fs.existsSync(logPath)) {
            res.write(`data: ${JSON.stringify({ source: 'system', message: `Waiting for log file at ${logPath}`, timestamp: new Date().toISOString() })}\n\n`);
            // Keep connection alive with heartbeats
            const hb = setInterval(() => res.write(':heartbeat\n\n'), 15000);
            req.on('close', () => clearInterval(hb));
            return;
        }

        const tail = spawn('tail', ['-f', '-n', '50', logPath]);
        tail.stdout.on('data', (data) => {
            data.toString().split('\n').forEach(line => {
                if (line.trim()) {
                    res.write(`data: ${JSON.stringify({ source: 'daemon', timestamp: new Date().toISOString(), message: line })}\n\n`);
                }
            });
        });
        tail.stderr.on('data', (d) => console.error('tail error:', d.toString()));
        req.on('close', () => { tail.kill(); });
        return;
    }

    // ── GET /api/tasks | PUT /api/tasks ─────────────────────────────────────
    if (url === '/api/tasks') {
        if (req.method === 'GET') {
            const tasks = readJSON(TASKS_FILE, []);
            return jsonResponse(res, tasks);
        }
        if (req.method === 'PUT') {
            const body = await parseBody(req);
            fs.writeFileSync(TASKS_FILE, JSON.stringify(body, null, 2));
            return jsonResponse(res, { success: true });
        }
        res.writeHead(405); res.end(); return;
    }

    // ── GET /api/agents ──────────────────────────────────────────────────────
    if (url === '/api/agents' && req.method === 'GET') {
        return jsonResponse(res, getAgents());
    }

    // ── GET /api/status (quick summary for Overview) ─────────────────────────
    if (url === '/api/status' && req.method === 'GET') {
        const tasks = readJSON(TASKS_FILE, []);
        const authReqs = readJSON(AUTH_REQUESTS_FILE, []);
        const agents = getAgents();
        const metrics = getSystemMetrics();
        return jsonResponse(res, {
            agentCount: agents.length,
            activeTasks: tasks.filter(t => t.status === 'in_progress' || t.status === 'inProgress').length,
            pendingApprovals: authReqs.length,
            cpu: metrics.cpu,
            memory: metrics.memory,
            uptime: metrics.uptime,
            timestamp: new Date().toISOString()
        });
    }

    // ── POST /api/agent (chat) ───────────────────────────────────────────────
    if (url === '/api/agent' && req.method === 'POST') {
        const body = await parseBody(req);
        const msg = body.message || '';
        // Echo back — the real integration point. When ZeroClaw IPC is available,
        // this should forward to the daemon. For now, acknowledge and log.
        console.log(`[chat] Message received: ${msg}`);
        return jsonResponse(res, {
            reply: `[ZeroClaw] Received: "${msg}". IPC bridge not yet active — run \`zeroclaw\` daemon and integrate stdin/stdout here.`,
            timestamp: new Date().toISOString()
        });
    }

    // ── GET /api/metrics ─────────────────────────────────────────────────────
    if (url === '/api/metrics' && req.method === 'GET') {
        return jsonResponse(res, getSystemMetrics());
    }

    // ── GET /api/processes ───────────────────────────────────────────────────
    if (url === '/api/processes' && req.method === 'GET') {
        return jsonResponse(res, getProcesses());
    }

    // ── GET /api/ledger ──────────────────────────────────────────────────────
    if (url === '/api/ledger' && req.method === 'GET') {
        return jsonResponse(res, getLedger());
    }

    // ── GET /api/pipelines ───────────────────────────────────────────────────
    if (url === '/api/pipelines' && req.method === 'GET') {
        return jsonResponse(res, readJSON(PIPELINES_FILE, []));
    }

    // ── GET /api/workspaces ──────────────────────────────────────────────────
    if (url === '/api/workspaces' && req.method === 'GET') {
        return jsonResponse(res, readJSON(WORKSPACES_FILE, []));
    }

    // ── GET /api/radar ───────────────────────────────────────────────────────
    if (url === '/api/radar' && req.method === 'GET') {
        return jsonResponse(res, readJSON(RADAR_FILE, { signals: [], trends: [], activeSignals: 0, processedToday: 0 }));
    }

    // ── GET /api/people ──────────────────────────────────────────────────────
    if (url === '/api/people' && req.method === 'GET') {
        return jsonResponse(res, readJSON(PEOPLE_FILE, []));
    }

    // ── GET /api/auth-requests  ──────────────────────────────────────────────
    if (url === '/api/auth-requests' && req.method === 'GET') {
        return jsonResponse(res, readJSON(AUTH_REQUESTS_FILE, []));
    }

    // ── POST /api/spawn-agent ───────────────────────────────────────────────
    if (url === '/api/spawn-agent' && req.method === 'POST') {
        try {
            const body = await parseBody(req);
            const name = body.name || `Agent-${Math.floor(Math.random() * 1000)}`;
            const id = `agent-${Date.now()}`;

            if (fs.existsSync(OPENCLAW_RC)) {
                const config = JSON.parse(fs.readFileSync(OPENCLAW_RC, 'utf8'));
                if (!config.agents) config.agents = { list: [], defaults: {} };
                if (!config.agents.list) config.agents.list = [];

                const newAgent = {
                    id,
                    name,
                    role: 'Autonomous Operative',
                    goal: 'Assist in mission-critical operations',
                    backstory: 'A highly capable ZeroClaw instance'
                };

                config.agents.list.push(newAgent);
                fs.writeFileSync(OPENCLAW_RC, JSON.stringify(config, null, 2));

                console.log(`[system] Spawned new agent: ${name} (${id})`);
                return jsonResponse(res, { success: true, agent: newAgent });
            } else {
                return jsonResponse(res, { error: 'openclaw.json not found' }, 404);
            }
        } catch (e) {
            console.error('[server] spawn-agent error:', e.message);
            return jsonResponse(res, { error: e.message }, 500);
        }
    }

    // ── POST /api/auth-requests/:id ──────────────────────────────────────────
    const authMatch = url.match(/^\/api\/auth-requests\/(.+)$/);
    if (authMatch && req.method === 'POST') {
        const id = authMatch[1];
        const body = await parseBody(req);
        const action = body.action; // 'approve' | 'reject'
        let requests = readJSON(AUTH_REQUESTS_FILE, []);
        requests = requests.filter(r => r.id !== id);
        fs.writeFileSync(AUTH_REQUESTS_FILE, JSON.stringify(requests, null, 2));
        console.log(`[auth] Request ${id} ${action}d`);
        return jsonResponse(res, { success: true, id, action });
    }

    // ── 404 fallthrough ──────────────────────────────────────────────────────
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: `No route for ${req.method} ${url}` }));
});

server.listen(PORT, '127.0.0.1', () => {
    console.log(`✅ ZeroClaw API bridge running on http://127.0.0.1:${PORT}`);
    console.log(`   Routes: /api/logs /api/tasks /api/agents /api/agent /api/metrics`);
    console.log(`           /api/processes /api/ledger /api/pipelines /api/workspaces`);
    console.log(`           /api/radar /api/people /api/auth-requests`);
});
