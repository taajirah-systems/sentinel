import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

interface SystemProcess {
  name: string;
  pid: string;
  cpu: number;
  memory: string;
  status: 'running' | 'sleeping' | 'zombie';
}

interface SystemMetric {
  label: string;
  value: string;
  color: string;
}

@Component({
  selector: 'app-system',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './system.html',
  styleUrl: './system.css',
})
export class System implements OnInit {
  private zeroclaw = inject(Zeroclaw);
  isConnected = this.zeroclaw.isConnected;
  readonly Math = Math; // expose for template

  processes = signal<SystemProcess[]>([]);
  metrics = signal<SystemMetric[]>([]);
  loading = signal(true);

  async ngOnInit() {
    await this.refresh();
    // Poll every 5 seconds for live updates
    setInterval(() => this.refresh(), 5000);
  }

  async refresh() {
    const [rawMetrics, rawProcesses] = await Promise.all([
      this.zeroclaw.getMetrics(),
      this.zeroclaw.getProcesses(),
    ]);

    if (rawMetrics) {
      this.metrics.set([
        { label: 'CPU Usage', value: rawMetrics.cpu ?? '—', color: 'emerald' },
        { label: 'Memory', value: rawMetrics.memory ?? '—', color: 'indigo' },
        { label: 'Disk', value: rawMetrics.disk ?? '—', color: 'amber' },
        { label: 'Network In', value: rawMetrics.network_in ?? '—', color: 'blue' },
        { label: 'Network Out', value: rawMetrics.network_out ?? '—', color: 'rose' },
        { label: 'Uptime', value: rawMetrics.uptime ?? '—', color: 'emerald' },
      ]);
    }

    if (rawProcesses?.length) {
      this.processes.set(rawProcesses);
    }

    this.loading.set(false);
  }

  getStatusColor(status: string) {
    switch (status) {
      case 'running': return 'text-emerald-400';
      case 'sleeping': return 'text-zinc-500';
      case 'zombie': return 'text-rose-400';
      default: return 'text-zinc-500';
    }
  }
}
