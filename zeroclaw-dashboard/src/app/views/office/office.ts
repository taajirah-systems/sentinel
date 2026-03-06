import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

interface Workspace {
  name: string;
  icon: string;
  tool: string;
  status: 'active' | 'idle' | 'offline';
  lastUsed: string;
  description: string;
}

@Component({
  selector: 'app-office',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './office.html',
  styleUrl: './office.css',
})
export class Office implements OnInit {
  private zeroclaw = inject(Zeroclaw);

  workspaces = signal<Workspace[]>([]);
  loading = signal(true);

  async ngOnInit() {
    const data = await this.zeroclaw.getWorkspaces();
    if (data?.length) this.workspaces.set(data);
    this.loading.set(false);
  }

  openAll() {
    this.workspaces()
      .filter(w => w.status === 'active')
      .forEach(w => console.log('Opening workspace:', w.name));
  }

  getStatusClass(status: string) {
    switch (status) {
      case 'active': return 'bg-emerald-500';
      case 'idle': return 'bg-zinc-600';
      case 'offline': return 'bg-rose-500';
      default: return 'bg-zinc-500';
    }
  }
}
