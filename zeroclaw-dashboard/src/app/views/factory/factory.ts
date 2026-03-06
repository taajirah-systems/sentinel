import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

interface Pipeline {
  name: string;
  stage: string;
  progress: number;
  status: 'running' | 'completed' | 'failed' | 'queued';
  agent: string;
  startTime: string;
  outputs: number;
}

@Component({
  selector: 'app-factory',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './factory.html',
  styleUrl: './factory.css',
})
export class Factory implements OnInit {
  private zeroclaw = inject(Zeroclaw);

  pipelines = signal<Pipeline[]>([]);
  loading = signal(true);

  active = computed(() => this.pipelines().filter(p => p.status === 'running').length);
  completed = computed(() => this.pipelines().filter(p => p.status === 'completed').length);
  failed = computed(() => this.pipelines().filter(p => p.status === 'failed').length);
  totalOutputs = computed(() => this.pipelines().reduce((sum, p) => sum + (p.outputs ?? 0), 0));

  async ngOnInit() {
    await this.load();
    // Refresh every 10 seconds
    setInterval(() => this.load(), 10000);
  }

  async load() {
    const data = await this.zeroclaw.getPipelines();
    if (data?.length) this.pipelines.set(data);
    this.loading.set(false);
  }

  getStatusClass(status: string) {
    switch (status) {
      case 'running': return 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400';
      case 'completed': return 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400';
      case 'failed': return 'bg-rose-500/10 border-rose-500/20 text-rose-400';
      case 'queued': return 'bg-zinc-500/10 border-zinc-500/20 text-zinc-500';
      default: return '';
    }
  }

  getProgressClass(status: string) {
    switch (status) {
      case 'running': return 'bg-emerald-500';
      case 'completed': return 'bg-indigo-500';
      case 'failed': return 'bg-rose-500';
      case 'queued': return 'bg-zinc-700';
      default: return 'bg-zinc-700';
    }
  }
}
