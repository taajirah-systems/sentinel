import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = "http://localhost:8000";

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stats, setStats] = useState({ total_actions: 0, high_risk_actions: 0, system_status: 'Loading...' });
  const [logs, setLogs] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    fetchLogs();
    fetchReports();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) { console.error("Stats fetch failed", err); }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/logs?limit=15`);
      const data = await res.json();
      setLogs(data);
    } catch (err) { console.error("Logs fetch failed", err); }
  };

  const fetchReports = async () => {
    try {
      const res = await fetch(`${API_BASE}/reports`);
      const data = await res.json();
      setReports(data);
      setLoading(false);
    } catch (err) { console.error("Reports fetch failed", err); }
  };

  const renderDashboard = () => (
    <div className="fade-in">
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Audit Events</div>
          <div className="stat-value">{stats.total_actions}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Security Incidents</div>
          <div className="stat-value" style={{color: 'var(--accent-primary)'}}>{stats.high_risk_actions}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Sentinel Engine</div>
          <div className="stat-value" style={{color: '#28c76f'}}>{stats.system_status}</div>
        </div>
      </div>

      <div className="data-section">
        <div className="section-header">
          <h2>Recent Audit Stream</h2>
          <button className="btn-primary" onClick={fetchLogs}>Refresh</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>Status</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(log => (
              <tr key={log.id}>
                <td style={{color: 'var(--text-secondary)'}}>{new Date(log.timestamp * 1000).toLocaleString()}</td>
                <td><code style={{background: 'rgba(255,255,255,0.05)', padding: '2px 4px'}}>{log.command}</code></td>
                <td>
                  <span className={`badge ${log.allowed ? 'badge-allowed' : 'badge-denied'}`}>
                    {log.allowed ? 'Allowed' : 'Denied'}
                  </span>
                </td>
                <td style={{fontWeight: '700'}}>{log.risk_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderReports = () => (
    <div className="data-section fade-in">
       <div className="section-header">
          <h2>Compliance Documents</h2>
        </div>
        <table>
          <thead>
            <tr>
              <th>Report Name</th>
              <th>Created</th>
              <th>Size</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((report, idx) => (
              <tr key={idx}>
                <td>{report.filename}</td>
                <td>{report.created_at}</td>
                <td>{(report.size / 1024).toFixed(1)} KB</td>
                <td>
                  <a href={`${API_BASE}/reports/${report.filename}`} target="_blank" rel="noreferrer">
                    <button className="btn-primary">Download</button>
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
    </div>
  );

  return (
    <div className="portal-container">
      <div className="sidebar">
        <div className="logo">
          <span>🦞</span> SOVEREIGN
        </div>
        <ul className="nav-menu">
          <li className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>Dashboard</li>
          <li className={`nav-item ${activeTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveTab('reports')}>Reports</li>
        </ul>
      </div>

      <main className="main-content">
        <header className="header">
          <h1>Sovereign Intelligence Portal</h1>
          <p>Real-time oversight of the autonomous Sentinel Swarm.</p>
        </header>

        {activeTab === 'dashboard' ? renderDashboard() : renderReports()}
      </main>
    </div>
  );
}

export default App;
