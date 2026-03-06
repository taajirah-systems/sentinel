import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

interface Signal {
  id: string;
  source: string;
  title: string;
  impact: 'High' | 'Medium' | 'Low' | 'Critical';
  type: string;
  relevance: number;
  timestamp: Date;
}

interface Trend {
  name: string;
  value: number;
  trend: 'up' | 'down' | 'flat';
}

@Component({
  selector: 'app-radar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './radar.html',
  styleUrl: './radar.css',
})
export class Radar implements OnInit {
  private zeroclaw = inject(Zeroclaw);

  signals = signal<Signal[]>([]);
  trends = signal<Trend[]>([]);
  activeSignals = signal(0);
  processedToday = signal(0);
  loading = signal(true);

  private pollInterval: any;

  async ngOnInit() {
    await this.refresh();
    this.pollInterval = setInterval(() => this.refresh(), 10000);
  }

  ngOnDestroy() {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  async refresh() {
    const data = await this.zeroclaw.getRadarSignals();
    this.signals.set(
      (data.signals ?? []).map((s: any) => ({ ...s, timestamp: new Date(s.timestamp) }))
    );
    this.trends.set(data.trends ?? []);
    this.activeSignals.set(data.activeSignals ?? 0);
    this.processedToday.set(data.processedToday ?? 0);
    this.loading.set(false);
  }

  getImpactClass(impact: string) {
    switch (impact) {
      case 'Critical': return 'text-purple-400 bg-purple-500/10 border-purple-500/20';
      case 'High': return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      case 'Medium': return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'Low': return 'text-zinc-500 bg-zinc-500/10 border-zinc-500/20';
      default: return 'text-zinc-500';
    }
  }
}
