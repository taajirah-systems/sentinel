import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './projects.html',
})
export class Projects {
  projects = [
    {
      id: 'PRJ-001',
      name: 'Mission Control OS',
      description: 'Building the ultimate ZeroClaw dashboard with live activity streams and Kanban management.',
      progress: 68,
      status: 'Active',
      priority: 'High',
      agents: ['A', 'C', 'H'],
      dueDate: 'Mar 15'
    },
    {
      id: 'PRJ-002',
      name: 'Sovereign Ledger System',
      description: 'Append-only ledger to track the Treasury state and integrate with boardroom reports.',
      progress: 90,
      status: 'Review',
      priority: 'High',
      agents: ['F', 'A'],
      dueDate: 'Mar 05'
    },
    {
      id: 'PRJ-003',
      name: 'Micro-SaaS Factory',
      description: 'Automated pipeline for generating and deploying micro-SaaS applications using the agent swarm.',
      progress: 25,
      status: 'Planning',
      priority: 'Medium',
      agents: ['Q', 'D'],
      dueDate: 'Apr 01'
    },
    {
      id: 'PRJ-004',
      name: 'Trend Radar Model',
      description: 'Global market analysis agent parsing news feeds and social trends to identify new opportunities.',
      progress: 10,
      status: 'Active',
      priority: 'Medium',
      agents: ['R'],
      dueDate: 'Mar 30'
    }
  ];
}
