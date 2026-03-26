import { useState } from 'react';
import { motion } from 'framer-motion';
import type { AgentType, AgentStatus } from '../types';

export const RobotHead = ({ color, status }: { color: string; status: AgentStatus }) => {
  return (
    <div className="relative preserve-3d" style={{ transform: 'translateZ(20px)' }}>
      {/* Front Face */}
      <motion.div 
        className="w-7 h-6 rounded-md border-2 border-white/80"
        style={{ backgroundColor: color }}
      >
        <div className="flex justify-around items-center h-full pt-1 px-1">
          <motion.div 
            className="w-1.5 h-1.5 bg-white rounded-full"
            animate={{ opacity: [1, 0.4, 1] }}
            transition={{ duration: 2.5, repeat: Infinity }}
          />
          <motion.div 
            className="w-1.5 h-1.5 bg-white rounded-full"
            animate={{ opacity: [1, 0.4, 1] }}
            transition={{ duration: 2.5, repeat: Infinity }}
          />
        </div>
      </motion.div>
      
      {/* Top Face */}
      <div 
        className="absolute top-0 left-0 w-7 h-[6px] origin-top"
        style={{ 
          backgroundColor: color, 
          filter: 'brightness(1.2)',
          transform: 'rotateX(-90deg)' 
        }}
      />
      
      {/* Side Face */}
      <div 
        className="absolute top-0 right-0 w-[6px] h-6 origin-right"
        style={{ 
          backgroundColor: color, 
          filter: 'brightness(0.7)',
          transform: 'rotateY(90deg)' 
        }}
      />

      {/* Antenna */}
      <motion.div 
        className="absolute -top-8 left-1/2 -translate-x-1/2 w-[0.5px] bg-white preserve-3d"
        animate={status === 'thinking' ? { height: [8, 12, 8] } : { height: 8 }}
        style={{ transform: 'translateZ(4px)' }}
      >
        <motion.div 
          className="absolute -top-2 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full"
          animate={status === 'thinking' ? { scale: [1, 1.4, 1] } : { scale: 1 }}
          style={{ 
            backgroundColor: status === 'idle' ? '#9ca3af' : 
                             status === 'working' ? '#22c55e' : 
                             status === 'collaborating' ? '#3b82f6' : '#a855f7' 
          }}
        />
      </motion.div>
    </div>
  );
};

export const RobotBody = ({ color, icon }: { color: string; icon: React.ReactNode }) => {
  return (
    <div className="relative preserve-3d" style={{ transform: 'translateZ(15px)' }}>
      {/* Front Face */}
      <div 
        className="w-8 h-8 rounded-md border-2 border-white/80 flex items-center justify-center"
        style={{ backgroundColor: color }}
      >
        <div className="text-white drop-shadow-md transform scale-75">
          {icon}
        </div>
      </div>
      
      {/* Top Face */}
      <div 
        className="absolute top-0 left-0 w-8 h-4 origin-top"
        style={{ 
          backgroundColor: color, 
          filter: 'brightness(1.3)',
          transform: 'rotateX(-90deg)' 
        }}
      />
      
      {/* Side Face */}
      <div 
        className="absolute top-0 right-0 w-4 h-8 origin-right"
        style={{ 
          backgroundColor: color, 
          filter: 'brightness(0.6)',
          transform: 'rotateY(90deg)' 
        }}
      />
    </div>
  );
};

export const RobotLimbs = ({ color, status }: { color: string; status: AgentStatus }) => {
  const isCollaborating = status === 'collaborating';
  const isWorking = status === 'working';

  return (
    <div className="preserve-3d">
      {/* Arms */}
      <motion.div 
        className="absolute top-2 -left-2 w-2 h-4 rounded-sm origin-top"
        style={{ backgroundColor: color, transform: 'translateZ(12px)' }}
        animate={isCollaborating ? { rotateZ: [-20, 20, -20] } : {}}
        transition={{ duration: 0.7, repeat: Infinity }}
      />
      <motion.div 
        className="absolute top-2 -right-2 w-2 h-4 rounded-sm origin-top"
        style={{ backgroundColor: color, transform: 'translateZ(12px)' }}
        animate={isCollaborating ? { rotateZ: [20, -20, 20] } : {}}
        transition={{ duration: 0.7, repeat: Infinity }}
      />

      {/* Legs */}
      <motion.div 
        className="absolute bottom-[-10px] left-1 w-2 h-5 rounded-sm origin-top"
        style={{ backgroundColor: color, transform: 'translateZ(10px)' }}
        animate={isWorking ? { scaleY: [1, 0.85, 1] } : {}}
        transition={{ duration: 0.5, repeat: Infinity }}
      />
      <motion.div 
        className="absolute bottom-[-10px] right-1 w-2 h-5 rounded-sm origin-top"
        style={{ backgroundColor: color, transform: 'translateZ(10px)' }}
        animate={isWorking ? { scaleY: [1, 0.85, 1] } : {}}
        transition={{ duration: 0.5, repeat: Infinity, delay: 0.25 }}
      />
    </div>
  );
};

export const Agent3D = ({ agent }: { agent: AgentType }) => {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      className="absolute top-0 left-0 preserve-3d"
      initial={false}
      animate={{ 
        x: agent.position.x, 
        y: agent.position.y,
        scale: isHovered ? 1.1 : 1
      }}
      transition={{ type: 'spring', stiffness: 80, damping: 15 }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Robot Shadow */}
      <div 
        className="absolute w-12 h-8 -left-2 -top-1 bg-black/60 rounded-full blur-md"
        style={{ transform: 'translateZ(-20px)' }}
      />

      {/* Movement Trail */}
      {agent.trail.map((pos, i) => (
        <div 
          key={i}
          className="absolute w-0.5 h-0.5 rounded-full"
          style={{ 
            backgroundColor: agent.color,
            opacity: (i / 15) * 0.6,
            left: pos.x - agent.position.x + 16,
            top: pos.y - agent.position.y + 16,
            transform: 'translateZ(2px)'
          }}
        />
      ))}

      {/* Glow Effect */}
      {(agent.status === 'working' || agent.status === 'collaborating') && (
        <motion.div 
          className="absolute -inset-4 rounded-full"
          style={{ backgroundColor: agent.color }}
          animate={{ scale: [1, 1.3, 1], opacity: [0.2, 0.5, 0.2] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}

      {/* Character Assembly */}
      <motion.div 
        className="preserve-3d"
        animate={agent.status === 'collaborating' ? { y: [0, -3, 0] } : {}}
        transition={{ duration: 0.6, repeat: Infinity }}
      >
        <RobotHead color={agent.color} status={agent.status} />
        <RobotBody color={agent.color} icon={agent.icon} />
        <RobotLimbs color={agent.color} status={agent.status} />
      </motion.div>

      {/* Name Tag */}
      <div 
        className="absolute -bottom-8 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-black/80 border border-cyber-cyan/30 rounded text-[9px] font-mono whitespace-nowrap"
        style={{ color: agent.color, transform: 'translateZ(25px)', borderColor: agent.color }}
      >
        {agent.name}
      </div>

      {/* Task Bubble */}
      {isHovered && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute bottom-[50px] left-1/2 -translate-x-1/2 w-48 p-3 bg-slate-900/90 border-2 backdrop-blur-md rounded-xl shadow-xl preserve-3d"
          style={{ borderColor: agent.color, transform: 'translateZ(40px)' }}
        >
          <div className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: agent.color }}>
            {agent.role}
          </div>
          <div className="text-xs text-cyber-cyan font-mono leading-tight">
            {agent.currentTask || "Idle: Waiting for sequence..."}
          </div>
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-900 border-r-2 border-b-2 rotate-45" style={{ borderColor: agent.color }} />
        </motion.div>
      )}
    </motion.div>
  );
};
