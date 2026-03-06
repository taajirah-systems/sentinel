import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { Zeroclaw } from '../../services/zeroclaw';
import { Router } from '@angular/router';

interface BadgeState {
  pendingApprovals: number;
  inProgressTasks: number;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css'
})
export class Sidebar implements OnInit, OnDestroy {
  public zeroClaw = inject(Zeroclaw);
  private zeroclaw = this.zeroClaw;
  private router = inject(Router);
  private pollInterval: any;

  pendingApprovals = signal(0);
  inProgressTasks = signal(0);

  async ngOnInit() {
    await this.refreshBadges();
    this.pollInterval = setInterval(() => this.refreshBadges(), 30000);
  }

  ngOnDestroy() {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  async refreshBadges() {
    try {
      const [tasks, authReqs] = await Promise.all([
        this.zeroclaw.getTasks(),
        this.zeroclaw.getAuthRequests(),
      ]);
      const inProgress = (tasks || []).filter((t: any) =>
        t.status === 'in_progress' || t.status === 'inProgress'
      ).length;
      this.inProgressTasks.set(inProgress);
      this.pendingApprovals.set((authReqs || []).length);
    } catch { /* silently fail */ }
  }

  navigate(route: string) {
    this.router.navigate([route]);
  }
}
