import { useState, useEffect, useRef } from 'react';
import { motion, useSpring, useMotionValue, AnimatePresence } from 'framer-motion';
import { 
  BarChart3, Code, Headset, BookOpen, 
  Network, Monitor, Radio
} from 'lucide-react';
import type { AgentType, Station } from '../types';
import { Agent3D } from './Agent3D';
import { Workstation3D } from './Workstation3D';

// --- Constants ---
const INITIAL_STATIONS: Station[] = [
  { id: 's1', name: 'Planning Station', type: 'Monitor', color: '#3b82f6', icon: <Monitor />, position: { x: 150, y: 150 } },
  { id: 's2', name: 'Analytics Hub', type: 'Database', color: '#10b981', icon: <BarChart3 />, position: { x: 450, y: 200 } },
  { id: 's3', name: 'Code Terminal', type: 'CPU', color: '#8b5cf6', icon: <Code />, position: { x: 750, y: 180 } },
  { id: 's4', name: 'Support Console', type: 'Server', color: '#f59e0b', icon: <Headset />, position: { x: 250, y: 450 } },
  { id: 's5', name: 'Research Lab', type: 'Workflow', color: '#ec4899', icon: <BookOpen />, position: { x: 550, y: 480 } },
  { id: 's6', name: 'Command Node', type: 'Radio', color: '#06b6d4', icon: <Radio />, position: { x: 800, y: 500 } },
];

const API_BASE = 'http://localhost:3001/api';

export const AgentRoom3D = () => {
  const [agents, setAgents] = useState<AgentType[]>([]);
  const [interactingPairs] = useState<Set<string>>(new Set());
  
  // Camera State
  const rotateX = useMotionValue(60);
  const rotateZ = useMotionValue(-45);
  const zoom = useMotionValue(1);

  const springRotateX = useSpring(rotateX, { stiffness: 100, damping: 30 });
  const springRotateZ = useSpring(rotateZ, { stiffness: 100, damping: 30 });
  const springZoom = useSpring(zoom, { stiffness: 100, damping: 30 });

  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  // Fetch Agents from Hub
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const res = await fetch(`${API_BASE}/agents`);
        const data = await res.json();
        
        setAgents(prev => {
          return data.map((newAgent: any) => {
            const existing = prev.find(a => a.id === newAgent.id);
            // Default position if not provided by real data
            const defaultPos = INITIAL_STATIONS[Math.floor(Math.random() * INITIAL_STATIONS.length)].position;
            
            return {
              ...newAgent,
              position: newAgent.position || existing?.position || defaultPos,
              icon: newAgent.icon || existing?.icon || <Network />,
              trail: existing?.trail || []
            };
          });
        });
      } catch (e) {
        console.error("Failed to sync agents:", e);
      }
    };

    const interval = setInterval(fetchAgents, 2000);
    fetchAgents();
    return () => clearInterval(interval);
  }, []);

  // Update Trails
  useEffect(() => {
    const interval = setInterval(() => {
      setAgents(prev => prev.map(agent => ({
        ...agent,
        trail: [...(agent.trail || []), agent.position].slice(-15)
      })));
    }, 150);
    return () => clearInterval(interval);
  }, []);

  // --- Interaction Handlers ---

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dx = (e.clientX - dragStart.current.x) * 0.3;
    const dy = (e.clientY - dragStart.current.y) * 0.3;

    rotateZ.set(rotateZ.get() + dx);
    const newRX = Math.min(80, Math.max(20, rotateX.get() - dy));
    rotateX.set(newRX);

    dragStart.current = { x: e.clientX, y: e.clientY };
  };

  const handleWheel = (e: React.WheelEvent) => {
    const newZoom = Math.min(1.5, Math.max(0.5, zoom.get() - e.deltaY * 0.001));
    zoom.set(newZoom);
  };

  return (
    <div 
      className={`relative w-full h-full perspective-1500 overflow-hidden cursor-${isDragging ? 'grabbing' : 'grab'}`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={() => setIsDragging(false)}
      onMouseLeave={() => setIsDragging(false)}
      onWheel={handleWheel}
    >
      {/* 3D Scene Wrapper */}
      <motion.div 
        className="w-[900px] h-[600px] absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 preserve-3d"
        style={{ 
          rotateX: springRotateX, 
          rotateZ: springRotateZ,
          scale: springZoom
        }}
      >
        {/* Floor Layers */}
        <div 
          className="absolute inset-0 bg-slate-950 shadow-[0_30px_80px_rgba(0,0,0,0.9)]"
          style={{ transform: 'translateZ(-40px)' }}
        />
        
        {/* Grid floor */}
        <motion.div 
          className="absolute inset-0 cyber-grid"
          animate={{ backgroundPosition: ['0px 0px', '40px 40px'] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          style={{ transform: 'translateZ(0px)' }}
        />

        {/* Sync Chamber */}
        <div 
          className="absolute top-[300px] left-[400px] w-[100px] h-[100px] flex items-center justify-center preserve-3d"
          style={{ transform: 'translateZ(5px)' }}
        >
          <motion.div 
            className="absolute inset-0 border-2 border-dashed border-cyber-purple/60 rounded-full bg-cyber-purple/5 shadow-[0_0_30px_rgba(168,85,247,0.4)]"
            animate={{ rotate: 360, scale: [1, 1.1, 1] }}
            transition={{ rotate: { duration: 8, repeat: Infinity, ease: 'linear' }, scale: { duration: 8, repeat: Infinity } }}
          />
        </div>

        {/* Environment Elements */}
        {INITIAL_STATIONS.map(station => (
          <Workstation3D key={station.id} station={station} />
        ))}

        {/* Agents */}
        {agents.map(agent => (
          <Agent3D key={agent.id} agent={agent} />
        ))}

        {/* Collaboration Lines (SVG) */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none preserve-3d" style={{ transform: 'translateZ(18px)' }}>
          <AnimatePresence>
            {Array.from(interactingPairs).map((id, i) => {
              if (i % 2 !== 0) return null;
              const a1 = agents.find(a => a.id === id);
              const a2 = agents.find(a => a.id === Array.from(interactingPairs)[i+1]);
              if (!a1 || !a2) return null;

              return (
                <motion.line
                  key={`${a1.id}-${a2.id}`}
                  x1={a1.position.x + 16}
                  y1={a1.position.y + 16}
                  x2={a2.position.x + 16}
                  y2={a2.position.y + 16}
                  stroke={a1.color}
                  strokeWidth="3"
                  strokeDasharray="8 4"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 0.8 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.8 }}
                />
              );
            })}
          </AnimatePresence>
        </svg>
      </motion.div>

      {/* Camera Stats UI */}
      <div className={`absolute bottom-6 left-6 flex flex-col gap-2 transition-opacity duration-300 ${isDragging ? 'opacity-50' : 'opacity-100'}`}>
        <div className="flex gap-4 text-[10px] font-mono text-cyber-cyan/60 uppercase">
          <span>Rot: {Math.round(rotateX.get())}° / {Math.round(rotateZ.get())}°</span>
          <span>Zoom: {Math.round(zoom.get() * 100)}%</span>
        </div>
        <div className="px-3 py-1 bg-black/40 border border-cyber-cyan/20 rounded-full text-[10px] text-cyber-cyan/80 font-mono">
          🎮 Drag to Rotate | 🖱️ Scroll to Zoom
        </div>
      </div>
    </div>
  );
};
