import { motion } from 'framer-motion';
import type { Station } from '../types';

export const Workstation3D = ({ station }: { station: Station }) => {
  return (
    <div 
      className="absolute top-0 left-0 preserve-3d"
      style={{ transform: `translate3d(${station.position.x}px, ${station.position.y}px, 0)` }}
    >
      {/* Station Base */}
      <div className="relative w-16 h-16 preserve-3d">
        {/* Front Face */}
        <div 
          className="absolute inset-0 rounded-xl border-2 flex items-center justify-center bg-black/40 backdrop-blur-sm shadow-[0_0_20px_rgba(6,182,212,0.3)]"
          style={{ 
            borderColor: station.color,
            color: station.color,
            transform: 'translateZ(8px)'
          }}
        >
          <motion.div
            animate={{ scale: [1, 1.1, 1], filter: ['drop-shadow(0 0 5px currentColor)', 'drop-shadow(0 0 15px currentColor)', 'drop-shadow(0 0 5px currentColor)'] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            {station.icon}
          </motion.div>
        </div>

        {/* Top Face */}
        <div 
          className="absolute top-0 left-0 w-16 h-8 origin-top"
          style={{ 
            backgroundColor: station.color, 
            opacity: 0.2,
            filter: 'brightness(1.4)',
            transform: 'rotateX(-90deg)' 
          }}
        />

        {/* Side Face */}
        <div 
          className="absolute top-0 right-0 w-8 h-16 origin-right"
          style={{ 
            backgroundColor: station.color, 
            opacity: 0.15,
            filter: 'brightness(0.8)',
            transform: 'rotateY(90deg)' 
          }}
        />

        {/* Point Light Effect (Ground Glow) */}
        <div 
          className="absolute -inset-8 rounded-full blur-2xl opacity-20"
          style={{ backgroundColor: station.color }}
        />
      </div>

      {/* Holographic Label */}
      <div 
        className="absolute -bottom-10 left-1/2 -translate-x-1/2 px-3 py-1 bg-black/80 border rounded-lg text-[10px] font-mono whitespace-nowrap shadow-lg shadow-black/50"
        style={{ 
          color: station.color, 
          borderColor: `${station.color}44`,
          transform: 'translateZ(15px)',
          textShadow: `0 0 8px ${station.color}`
        }}
      >
        {station.name.toUpperCase()}
      </div>
    </div>
  );
};
