const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');
const dotenv = require('dotenv');

// Load .env from root
dotenv.config({ path: path.join(__dirname, '../../.env') });

const app = express();
const PORT = 3001;
const SENTINEL_API = process.env.SENTINEL_HOST === '0.0.0.0' ? 'http://localhost:8765' : `http://${process.env.SENTINEL_HOST || 'localhost'}:${process.env.SENTINEL_PORT || '8765'}`;
const SENTINEL_TOKEN = process.env.SENTINEL_AUTH_TOKEN;

app.use(cors());
app.use(bodyParser.json());

// In-memory state store
let agents = {
  'a1': { id: 'a1', name: 'Prime', role: 'Lead Architect', status: 'idle', color: '#3b82f6', currentTask: 'Analyzing System Topology' },
  'a2': { id: 'a2', name: 'Sage', role: 'Security Oracle', status: 'thinking', color: '#10b981', currentTask: 'Evaluating ROI Risk' },
  'a3': { id: 'a3', name: 'Cipher', role: 'Security Auditor', status: 'idle', color: '#8b5cf6', currentTask: 'Monitoring Sentinel Gates' },
  'a4': { id: 'a4', name: 'Ghost', role: 'Infiltration', status: 'idle', color: '#f59e0b', currentTask: 'Stealth Audit Active' },
  'a5': { id: 'a5', name: 'Nova', role: 'Research Asst', status: 'idle', color: '#ec4899', currentTask: 'Awaiting Findings' },
  'a6': { id: 'a6', name: 'Pulse', role: 'Network Admin', status: 'idle', color: '#06b6d4', currentTask: 'Scanning Neural Bridge' },
};

// Log history
let logs = [];

// API Endpoints
app.get('/api/agents', (req, res) => {
  res.json(Object.values(agents));
});

app.post('/api/agents/:id', (req, res) => {
  const { id } = req.params;
  const { status, currentTask, position, name, role, color } = req.body;

  if (agents[id]) {
    agents[id] = { ...agents[id], ...req.body };
  } else {
    agents[id] = { id, ...req.body };
  }

  // Auto-log updates
  if (currentTask) {
    logs.push({
      id: Math.random().toString(36).substring(2, 11),
      msg: `${agents[id].name || id}: ${currentTask}`,
      time: new Date().toLocaleTimeString()
    });
    if (logs.length > 50) logs.shift();
  }

  res.json({ success: true, agent: agents[id] });
});

app.get('/api/logs', async (req, res) => {
  let combinedLogs = [...logs];
  
  try {
    const response = await fetch(`${SENTINEL_API}/logs?limit=50`, {
      headers: { 'x-sentinel-token': SENTINEL_TOKEN }
    });
    
    if (response.ok) {
      const sentinelLogs = await response.json();
      const mappedLogs = sentinelLogs.map(log => ({
        id: `sentinel_${log.id}`,
        msg: `[SENTINEL] ${log.command} -> ${log.allowed ? 'ALLOWED' : 'BLOCKED'} (${log.reason})`,
        time: new Date(log.timestamp * 1000).toLocaleTimeString(),
        type: 'sentinel',
        risk_score: log.risk_score
      }));
      combinedLogs = [...combinedLogs, ...mappedLogs];
      // Sort by time (this is tricky with locale strings, but for now we'll just append)
    }
  } catch (err) {
    console.error('Failed to fetch Sentinel logs:', err.message);
  }

  res.json(combinedLogs);
});

app.post('/api/logs', (req, res) => {
  const { msg } = req.body;
  const log = {
    id: Math.random().toString(36).substring(2, 11),
    msg,
    time: new Date().toLocaleTimeString()
  };
  logs.push(log);
  if (logs.length > 50) logs.shift();
  res.json(log);
});

app.listen(PORT, () => {
  console.log(`Federation Hub running on http://localhost:${PORT}`);
});
