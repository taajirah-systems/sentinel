import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Zeroclaw } from '../../services/zeroclaw';

type LogLevel = 'all' | 'info' | 'warn' | 'error' | 'debug';

@Component({
  selector: 'app-logs-feed',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './logs-feed.html',
  styleUrl: './logs-feed.css'
})
export class LogsFeed implements OnInit, OnDestroy {
  public zeroClaw = inject(Zeroclaw);

  searchQuery = signal('');
  activeFilter = signal<LogLevel>('all');
  autoScroll = signal(true);
  private scrollInterval: any;

  filters: { label: string; value: LogLevel; color: string }[] = [
    { label: 'ALL', value: 'all', color: 'text-zinc-400 border-zinc-700' },
    { label: 'INFO', value: 'info', color: 'text-blue-400 border-blue-700' },
    { label: 'WARN', value: 'warn', color: 'text-amber-400 border-amber-700' },
    { label: 'ERROR', value: 'error', color: 'text-rose-400 border-rose-700' },
    { label: 'DEBUG', value: 'debug', color: 'text-purple-400 border-purple-700' },
  ];

  filteredLogs = computed(() => {
    const all = this.zeroClaw.logs();
    const q = this.searchQuery().toLowerCase();
    const f = this.activeFilter();

    return all.filter(log => {
      const msg = this.extractMessage(log).toLowerCase();
      const level = this.detectLevel(log);
      const matchesSearch = !q || msg.includes(q);
      const matchesFilter = f === 'all' || level === f;
      return matchesSearch && matchesFilter;
    }).slice(-200); // cap to last 200 for perf
  });

  logCounts = computed(() => {
    const all = this.zeroClaw.logs();
    return {
      total: all.length,
      errors: all.filter(l => this.detectLevel(l) === 'error').length,
      warnings: all.filter(l => this.detectLevel(l) === 'warn').length,
    };
  });

  ngOnInit() {
    // Re-scroll to bottom when new logs come in (if enabled)
    this.scrollInterval = setInterval(() => {
      if (this.autoScroll()) {
        const el = document.getElementById('log-scroll-anchor');
        el?.scrollIntoView({ behavior: 'smooth' });
      }
    }, 2000);
  }

  ngOnDestroy() {
    if (this.scrollInterval) clearInterval(this.scrollInterval);
  }

  setFilter(f: LogLevel) { this.activeFilter.set(f); }

  extractMessage(log: any): string {
    return log?.message || log?.data?.content || log?.data?.message ||
      (typeof log?.data === 'string' ? log.data : '') ||
      JSON.stringify(log?.data || log);
  }

  extractTimestamp(log: any): string {
    const ts = log?.timestamp || log?.data?.timestamp;
    if (!ts) return '';
    try { return new Date(ts).toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
    catch { return ts.substring(11, 19) || ''; }
  }

  extractSource(log: any): string {
    return log?.source || log?.type || 'daemon';
  }

  detectLevel(log: any): LogLevel {
    const msg = this.extractMessage(log).toLowerCase();
    if (msg.includes('error') || msg.includes('err ') || msg.includes('failed') || msg.includes('exception')) return 'error';
    if (msg.includes('warn') || msg.includes('warning')) return 'warn';
    if (msg.includes('debug') || msg.includes('[debug]')) return 'debug';
    return 'info';
  }

  getMessageClass(log: any): string {
    const level = this.detectLevel(log);
    switch (level) {
      case 'error': return 'text-rose-400';
      case 'warn': return 'text-amber-300';
      case 'debug': return 'text-purple-400';
      default: return 'text-neutral-300';
    }
  }

  getSourceClass(source: string): string {
    switch (source) {
      case 'daemon': return 'text-blue-400';
      case 'agent': return 'text-emerald-400';
      case 'system': return 'text-zinc-400';
      default: return 'text-cyan-400';
    }
  }

  getLevelBadge(log: any): string {
    const level = this.detectLevel(log);
    switch (level) {
      case 'error': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      case 'warn': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'debug': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      default: return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    }
  }

  getLevelLabel(log: any): string {
    return this.detectLevel(log).toUpperCase();
  }

  clearSearch() { this.searchQuery.set(''); }
}
