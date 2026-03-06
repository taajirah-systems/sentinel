import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

interface AuthRequest {
  id: string;
  type: 'security' | 'financial' | 'operational';
  title: string;
  description: string;
  requester: string;
  timestamp: string;
  urgency: 'low' | 'medium' | 'high';
}

@Component({
  selector: 'app-approvals',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './approvals.html',
  styleUrl: './approvals.css',
})
export class Approvals implements OnInit, OnDestroy {
  private zeroclaw = inject(Zeroclaw);
  private pollInterval: any;

  reviewTasks = signal<any[]>([]);
  authRequests = signal<AuthRequest[]>([]);
  loading = signal(true);
  lastUpdated = signal<Date | null>(null);

  async ngOnInit() {
    await this.refresh();
    this.pollInterval = setInterval(() => this.refresh(), 15000);
  }

  ngOnDestroy() {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  async refresh() {
    const [tasks, authReqs] = await Promise.all([
      this.zeroclaw.getTasks(),
      this.zeroclaw.getAuthRequests(),
    ]);
    this.reviewTasks.set(tasks.filter((t: any) => t.status === 'review'));
    if (authReqs?.length) this.authRequests.set(authReqs);
    this.loading.set(false);
    this.lastUpdated.set(new Date());
  }

  async approve(id: string) {
    await this.zeroclaw.resolveAuthRequest(id, 'approve');
    this.authRequests.update(reqs => reqs.filter(r => r.id !== id));
  }

  async reject(id: string) {
    await this.zeroclaw.resolveAuthRequest(id, 'reject');
    this.authRequests.update(reqs => reqs.filter(r => r.id !== id));
  }

  getTypeClass(type: string) {
    switch (type) {
      case 'security': return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      case 'financial': return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'operational': return 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20';
      default: return 'text-zinc-400 bg-zinc-500/10 border-zinc-500/20';
    }
  }

  getUrgencyClass(urgency: string) {
    switch (urgency) {
      case 'high': return 'text-rose-400';
      case 'medium': return 'text-amber-400';
      case 'low': return 'text-zinc-500';
      default: return 'text-zinc-500';
    }
  }
}
