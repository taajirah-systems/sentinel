import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

@Component({
  selector: 'app-system-health',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './system-health.html',
  styleUrl: './system-health.css',
})
export class SystemHealth {
  private zeroclaw = inject(Zeroclaw);
  isConnected = this.zeroclaw.isConnected;

  recentLogs = computed(() => this.zeroclaw.logs().slice(-50).reverse());

  logCount = computed(() => this.zeroclaw.logs().length);

  services = [
    { name: 'ZeroClaw SSE Feed', description: 'Real-time event stream from daemon' },
    { name: 'API Gateway (:4301)', description: 'Task & agent REST endpoints' },
    { name: 'Angular App (:4300)', description: 'Mission Control frontend' },
    { name: 'Telegram Bot', description: 'External command ingestion' },
  ];

  getLogClass(msg: string = '') {
    if (msg.includes('WARN') || msg.includes('⚠️')) return 'text-amber-400';
    if (msg.includes('ERROR') || msg.includes('❌')) return 'text-rose-400';
    if (msg.includes('🤖') || msg.includes('Reply')) return 'text-emerald-400';
    if (msg.includes('💬') || msg.includes('telegram')) return 'text-blue-400';
    return 'text-zinc-500';
  }
}
