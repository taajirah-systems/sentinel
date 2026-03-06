import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface ScheduleItem {
  id: string;
  time: string;
  agent: string;
  agentInitial: string;
  agentColor: string;
  task: string;
  target: string;
  status: 'completed' | 'running' | 'upcoming';
}

@Component({
  selector: 'app-calendar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './calendar.html',
  styleUrl: './calendar.css',
})
export class Calendar {
  public today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });

  public alwaysRunning = [
    { name: 'Trend Radar Scraper', agent: 'Researcher', color: 'bg-emerald-600' },
    { name: 'System Pulse Monitor', agent: 'Architect', color: 'bg-indigo-600' },
    { name: 'Gateway Health Watch', agent: 'DevOps', color: 'bg-orange-600' }
  ];

  public schedule: ScheduleItem[] = [
    {
      id: 'SCH-01',
      time: '08:00 AM',
      agent: 'Architect',
      agentInitial: 'A',
      agentColor: 'bg-purple-600',
      task: 'System Health Check & Resource Provisioning',
      target: 'Mission Control Cluster',
      status: 'completed'
    },
    {
      id: 'SCH-02',
      time: '09:30 AM',
      agent: 'Coder',
      agentInitial: 'C',
      agentColor: 'bg-blue-600',
      task: 'Feature branch synthesis',
      target: 'PRJ-002: Sovereign Ledger',
      status: 'completed'
    },
    {
      id: 'SCH-03',
      time: '11:00 AM',
      agent: 'DevOps',
      agentInitial: 'D',
      agentColor: 'bg-orange-600',
      task: 'Deploy staging environment & run E2E',
      target: 'Micro-SaaS Pipeline',
      status: 'running'
    },
    {
      id: 'SCH-04',
      time: '01:00 PM',
      agent: 'TechWriter',
      agentInitial: 'T',
      agentColor: 'bg-emerald-600',
      task: 'Generate automated changelogs and API specs',
      target: 'ZeroClaw Core Repo',
      status: 'upcoming'
    },
    {
      id: 'SCH-05',
      time: '03:45 PM',
      agent: 'Architect',
      agentInitial: 'A',
      agentColor: 'bg-purple-600',
      task: 'Daily Boardroom Synthesis Report',
      target: 'Swarm Council',
      status: 'upcoming'
    }
  ];

  getStatusColor(status: string): string {
    switch (status) {
      case 'completed': return 'border-emerald-500/50 text-emerald-400 bg-emerald-500/10';
      case 'running': return 'border-blue-500/50 text-blue-400 bg-blue-500/10';
      case 'upcoming': return 'border-zinc-700 text-zinc-400 bg-zinc-800/50';
      default: return 'border-zinc-700 text-zinc-400 bg-zinc-800/50';
    }
  }

  getStatusIcon(status: string): string {
    switch (status) {
      case 'completed': return '✓';
      case 'running': return '⟳';
      case 'upcoming': return '○';
      default: return '○';
    }
  }
}
