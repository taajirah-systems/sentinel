import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Zeroclaw } from '../../services/zeroclaw';

export interface Agent {
  id: string;
  name: string;
  status: string;
  model: string;
  tasksActive: number;
}

@Component({
  selector: 'app-agents',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './agents.html',
  styleUrl: './agents.css',
})
export class Agents implements OnInit, OnDestroy {
  private zeroclaw = inject(Zeroclaw);
  private router = inject(Router);
  private pollInterval: any;

  public agents = signal<Agent[]>([]);
  public loading = signal(true);
  public lastUpdated = signal<Date | null>(null);

  async ngOnInit() {
    await this.refresh();
    this.pollInterval = setInterval(() => this.refresh(), 10000);
  }

  ngOnDestroy() {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  async refresh() {
    try {
      const data = await this.zeroclaw.getAgents();
      this.agents.set(data || []);
      this.loading.set(false);
      this.lastUpdated.set(new Date());
    } catch (error) {
      console.error('Failed to refresh agents:', error);
      this.loading.set(false);
    }
  }

  async spawnAgent() {
    try {
      const name = prompt('Enter a name for the new mission agent:');
      if (!name) return;

      const result = await this.zeroclaw.spawnAgent(name);
      if (result.success) {
        alert(`Successfully spawned agent: ${result.agent.name}`);
        await this.refresh();
      }
    } catch (error) {
      alert('Failed to spawn agent. Check console for details.');
    }
  }

  openChat(agent: Agent) {
    this.router.navigate(['/chat'], { queryParams: { agent: agent.name } });
  }
}
