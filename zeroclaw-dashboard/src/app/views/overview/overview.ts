import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Zeroclaw } from '../../services/zeroclaw';

interface StatCard {
    label: string;
    value: number | string;
    icon: string;
    color: string;
    route: string;
    subtitle?: string;
}

@Component({
    selector: 'app-overview',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './overview.html',
    styleUrl: './overview.css',
})
export class Overview implements OnInit, OnDestroy {
    private zeroclaw = inject(Zeroclaw);
    private router = inject(Router);
    private pollInterval: any;

    isConnected = this.zeroclaw.isConnected;
    logs = this.zeroclaw.logs;

    loading = signal(true);
    agentCount = signal(0);
    activeTasks = signal(0);
    pendingApprovals = signal(0);
    cpuUsage = signal('—');
    uptime = signal('—');
    memoryUsage = signal('—');
    lastUpdated = signal<Date | null>(null);

    recentLogs = computed(() =>
        this.logs().slice(-6).reverse()
    );

    statCards = computed<StatCard[]>(() => [
        {
            label: 'Agents Online',
            value: this.agentCount(),
            icon: 'agent',
            color: 'emerald',
            route: '/agents',
            subtitle: 'Swarm active'
        },
        {
            label: 'Active Tasks',
            value: this.activeTasks(),
            icon: 'tasks',
            color: 'purple',
            route: '/tasks',
            subtitle: 'In progress'
        },
        {
            label: 'Pending Auth',
            value: this.pendingApprovals(),
            icon: 'shield',
            color: 'amber',
            route: '/approvals',
            subtitle: 'Awaiting review'
        },
        {
            label: 'CPU Load',
            value: this.cpuUsage(),
            icon: 'cpu',
            color: 'blue',
            route: '/system',
            subtitle: this.uptime()
        },
    ]);

    quickLinks = [
        { label: 'Tasks Kanban', route: '/tasks', icon: 'kanban', color: 'purple' },
        { label: 'Agent Swarm', route: '/agents', icon: 'agent', color: 'emerald' },
        { label: 'Chat', route: '/chat', icon: 'chat', color: 'indigo' },
        { label: 'Approvals', route: '/approvals', icon: 'shield', color: 'amber' },
        { label: 'Treasury', route: '/treasury', icon: 'treasury', color: 'green' },
        { label: 'Radar', route: '/radar', icon: 'radar', color: 'orange' },
        { label: 'Factory', route: '/factory', icon: 'factory', color: 'rose' },
        { label: 'System', route: '/system', icon: 'system', color: 'blue' },
    ];

    async ngOnInit() {
        await this.refresh();
        this.pollInterval = setInterval(() => this.refresh(), 10000);
    }

    ngOnDestroy() {
        if (this.pollInterval) clearInterval(this.pollInterval);
    }

    async refresh() {
        const [agents, tasks, authReqs, metrics] = await Promise.all([
            this.zeroclaw.getAgents(),
            this.zeroclaw.getTasks(),
            this.zeroclaw.getAuthRequests(),
            this.zeroclaw.getMetrics(),
        ]);

        this.agentCount.set((agents || []).length);

        const inProgress = (tasks || []).filter((t: any) =>
            t.status === 'in_progress' || t.status === 'inProgress'
        ).length;
        this.activeTasks.set(inProgress);

        this.pendingApprovals.set((authReqs || []).length);

        if (metrics) {
            this.cpuUsage.set(metrics.cpu || '—');
            this.uptime.set(metrics.uptime || '—');
            this.memoryUsage.set(metrics.memory || '—');
        }

        this.loading.set(false);
        this.lastUpdated.set(new Date());
    }

    navigate(route: string) {
        this.router.navigate([route]);
    }

    getColorClasses(color: string): { bg: string; border: string; text: string; icon: string } {
        const map: Record<string, any> = {
            emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', text: 'text-emerald-400', icon: 'text-emerald-500' },
            purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/20', text: 'text-purple-400', icon: 'text-purple-500' },
            amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-400', icon: 'text-amber-500' },
            blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-400', icon: 'text-blue-500' },
            indigo: { bg: 'bg-indigo-500/10', border: 'border-indigo-500/20', text: 'text-indigo-400', icon: 'text-indigo-500' },
            green: { bg: 'bg-green-500/10', border: 'border-green-500/20', text: 'text-green-400', icon: 'text-green-500' },
            orange: { bg: 'bg-orange-500/10', border: 'border-orange-500/20', text: 'text-orange-400', icon: 'text-orange-500' },
            rose: { bg: 'bg-rose-500/10', border: 'border-rose-500/20', text: 'text-rose-400', icon: 'text-rose-500' },
        };
        return map[color] || map['blue'];
    }

    formatLogSource(log: any): string {
        return log?.source || log?.type || 'daemon';
    }

    formatLogMessage(log: any): string {
        const msg = log?.message || log?.data?.content || log?.data?.message || JSON.stringify(log?.data || log);
        return typeof msg === 'string' ? msg.slice(0, 80) : JSON.stringify(msg).slice(0, 80);
    }

    formatLogTime(log: any): string {
        const ts = log?.timestamp || log?.data?.timestamp;
        if (!ts) return '';
        try { return new Date(ts).toLocaleTimeString(); } catch { return ''; }
    }

    sourceColor(source: string): string {
        if (source === 'daemon') return 'text-blue-400';
        if (source === 'agent') return 'text-emerald-400';
        return 'text-zinc-500';
    }
}
