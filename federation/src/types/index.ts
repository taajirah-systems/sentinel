import React from 'react';

export interface Position {
  x: number;
  y: number;
}

export type AgentStatus = 'idle' | 'working' | 'collaborating' | 'thinking';

export interface AgentType {
  id: string;
  name: string;
  role: string;
  color: string;
  icon: React.ReactNode;
  position: Position;
  status: AgentStatus;
  currentTask?: string;
  trail: Position[];
}

export interface Station {
  id: string;
  name: string;
  type: string;
  color: string;
  icon: React.ReactNode;
  position: Position;
}
