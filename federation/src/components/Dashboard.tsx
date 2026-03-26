import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Activity, Users, Layers } from 'lucide-react';
import { AgentRoom3D } from './AgentRoom3D';

interface LogEntry {
  id: string;
  msg: string;
  time: string;
  type?: 'sentinel' | 'system';
  risk_score?: number;
}

const API_BASE = 'http://localhost:3001/api';

export const Dashboard = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [activeCount] = useState(6);

  const fetchLogs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/logs`);
      const data = await res.json();
      setLogs(data.reverse()); // Show newest at top
    } catch (e) {
      console.error("Failed to sync logs:", e);
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(fetchLogs, 2000);
    fetchLogs();
    return () => clearInterval(interval);
  }, [fetchLogs]);

  return (
    <div className="flex flex-col w-screen h-screen bg-slate-950 text-cyber-cyan p-6 gap-6 overflow-hidden">
      {/* Header UI */}
      <header className="flex justify-between items-center p-5 bg-black/60 backdrop-blur-xl border border-cyber-cyan/30 rounded-2xl shadow-[0_0_30px_rgba(6,182,212,0.15)]">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-cyber-cyan/10 rounded-xl border border-cyber-cyan/40 shadow-[0_0_15px_rgba(6,182,212,0.3)]">
            <Zap className="w-8 h-8 text-cyber-cyan animate-pulse" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tighter bg-gradient-to-r from-cyber-cyan to-cyber-blue bg-clip-text text-transparent">
              OPENCLAW AGENT COMMAND CENTER
            </h1>
            <p className="text-xs font-mono text-cyber-cyan/60 uppercase tracking-widest flex items-center gap-2">
              Neural Network Monitoring System v3.0 <span className="w-1.5 h-1.5 bg-cyber-cyan rounded-full animate-ping" />
            </p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="px-5 py-3 bg-black/80 border border-cyber-cyan/40 rounded-xl flex flex-col items-center min-w-[100px] shadow-[0_0_15px_rgba(6,182,212,0.2)]">
            <span className="text-[10px] font-mono text-cyber-cyan/50 uppercase">Active Agents</span>
            <span className="text-xl font-bold text-cyber-cyan [text-shadow:0_0_10px_currentColor]">0{activeCount}</span>
          </div>
          <div className="px-5 py-3 bg-black/80 border border-cyber-green/40 rounded-xl flex flex-col items-center min-w-[100px] shadow-[0_0_15px_rgba(34,197,94,0.15)]">
            <span className="text-[10px] font-mono text-cyber-green/50 uppercase">Operational</span>
            <span className="text-xl font-bold text-cyber-green drop-shadow-[0_0_8px_rgba(34,197,94,0.6)]">100%</span>
          </div>
        </div>
      </header>

      <div className="flex flex-1 gap-6 min-h-0">
        {/* Main 3D Viewport */}
        <div className="flex-[3] bg-black/40 border border-cyber-cyan/20 rounded-2xl relative shadow-inner shadow-cyan-900/10">
          <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-cyber-cyan/20 to-transparent top-0" />
          <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-cyber-cyan/10 to-transparent bottom-0" />
          <AgentRoom3D />
          
          {/* Scanline Effect Overlay */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-[0.03]">
            <div className="w-full h-[2px] bg-white animate-scanline" />
          </div>
        </div>

        {/* Activity Feed Panel */}
        <aside className="w-[340px] flex flex-col gap-4">
          {/* Logs Section */}
          <section className="flex-1 flex flex-col bg-black/60 backdrop-blur-md border border-cyber-cyan/20 rounded-2xl overflow-hidden min-h-0">
            <div className="p-4 border-b border-cyber-cyan/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyber-cyan animate-pulse" />
                <h2 className="text-sm font-bold uppercase tracking-wider">System Log</h2>
              </div>
              <span className="text-[10px] font-mono p-1 px-2 bg-cyber-cyan/10 rounded-md">LIVE_FEED</span>
            </div>
            
            <div className="flex-1 p-4 overflow-y-auto space-y-3 font-mono text-[11px] scrollbar-hide">
              <AnimatePresence initial={false}>
                {logs.length === 0 ? (
                  <div className="text-cyber-cyan/30 text-center mt-10 italic">Awaiting neural pulse...</div>
                ) : (
                  logs.map(log => (
                    <motion.div
                      key={log.id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={`p-3 border rounded-lg flex flex-col gap-1 ${
                        log.type === 'sentinel' 
                          ? (log.msg.includes('ALLOWED') ? 'bg-cyber-green/5 border-cyber-green/20' : 'bg-red-500/5 border-red-500/20')
                          : 'bg-cyber-cyan/5 border-cyber-cyan/10'
                      }`}
                    >
                      <div className="flex justify-between items-center opacity-40">
                        <span className="text-[9px] font-bold">
                          {log.type === 'sentinel' ? 'SENTINEL_AUDIT' : 'ENCRYPTED_SIG'}
                        </span>
                        <span>{log.time}</span>
                      </div>
                      <div className={`leading-tight ${
                        log.type === 'sentinel'
                          ? (log.msg.includes('ALLOWED') ? 'text-cyber-green' : 'text-red-400')
                          : 'text-cyber-cyan/90'
                      }`}>
                        <span className="mr-1">&gt;</span> {log.msg}
                      </div>
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
            </div>
          </section>

          {/* Roster & Keys */}
          <section className="p-4 bg-black/60 backdrop-blur-md border border-cyber-cyan/20 rounded-2xl space-y-4">
            <div className="space-y-2">
              <h3 className="text-[10px] font-bold text-cyber-cyan/40 uppercase tracking-[0.2em] flex items-center gap-2">
                <Users className="w-3 h-3" /> Agent Roster
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {['Atlas', 'Sage', 'Cipher', 'Nova', 'Echo', 'Nexus'].map((name, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px]">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyber-cyan animate-pulse" />
                    <span className="opacity-70">{name}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-cyber-cyan/10 space-y-2">
              <h3 className="text-[10px] font-bold text-cyber-cyan/40 uppercase tracking-[0.2em] flex items-center gap-2">
                <Layers className="w-3 h-3" /> Status Key
              </h3>
              <div className="grid grid-cols-2 gap-y-1 text-[9px] uppercase font-mono">
                <div className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-cyber-green" /> Working</div>
                <div className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-cyber-blue" /> Syncing</div>
                <div className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-cyber-purple" /> Thinking</div>
                <div className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-slate-500" /> Idle</div>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
};
