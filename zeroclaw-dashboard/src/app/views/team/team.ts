import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

interface Person {
  id?: string;
  name: string;
  role: string;
  status: string;
  expertise?: string[];
  type?: string;
}

@Component({
  selector: 'app-team',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './team.html',
  styleUrl: './team.css',
})
export class Team implements OnInit, OnDestroy {
  private zeroclaw = inject(Zeroclaw);
  private pollInterval: any;

  people: Person[] = [];
  loading = true;
  lastUpdated: Date | null = null;

  async ngOnInit() {
    await this.refresh();
    this.pollInterval = setInterval(() => this.refresh(), 30000);
  }

  ngOnDestroy() {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  async refresh() {
    try {
      const data = await this.zeroclaw.getPeople();
      if (data?.length) this.people = data;
    } catch (e) {
      console.error('Team refresh error:', e);
    }
    this.loading = false;
    this.lastUpdated = new Date();
  }

  getStatusColor(status: string): string {
    switch ((status || '').toLowerCase()) {
      case 'online':
      case 'active': return 'bg-emerald-500';
      case 'idle': return 'bg-amber-500';
      case 'offline': return 'bg-zinc-600';
      default: return 'bg-zinc-600';
    }
  }

  getStatusText(status: string): string {
    return (status || 'unknown').toLowerCase();
  }

  getTypeClass(type: string): string {
    switch ((type || '').toLowerCase()) {
      case 'agent': return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
      case 'human': return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      default: return 'text-zinc-400 bg-zinc-500/10 border-zinc-500/20';
    }
  }
}
