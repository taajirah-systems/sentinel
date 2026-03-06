import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

interface Person {
  name: string;
  role: string;
  avatar: string;
  status: 'online' | 'offline' | 'busy';
  expertise: string[];
  recentActivity: string;
  partnerAgent?: string;
  missions?: number;
  efficiency?: number;
  authority?: string;
}

@Component({
  selector: 'app-people',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './people.html',
  styleUrl: './people.css',
})
export class People implements OnInit {
  private zeroclaw = inject(Zeroclaw);

  teamMembers = signal<Person[]>([]);
  selectedName = signal<string | null>(null);
  loading = signal(true);

  selected = computed(() => {
    const members = this.teamMembers();
    if (!members.length) return null;
    const name = this.selectedName();
    return members.find(m => m.name === name) ?? members[0];
  });

  async ngOnInit() {
    const data = await this.zeroclaw.getPeople();
    if (data?.length) {
      this.teamMembers.set(data);
      this.selectedName.set(data[0].name);
    }
    this.loading.set(false);
  }

  selectPerson(name: string) {
    this.selectedName.set(name);
  }

  getStatusClass(status: string) {
    switch (status) {
      case 'online': return 'bg-emerald-500';
      case 'offline': return 'bg-zinc-700';
      case 'busy': return 'bg-amber-500';
      default: return 'bg-zinc-500';
    }
  }
}
