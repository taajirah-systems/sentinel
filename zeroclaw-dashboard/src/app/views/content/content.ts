import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface ContentItem {
  id: string;
  platform: 'Twitter' | 'LinkedIn' | 'Blog';
  content: string;
  authorAgent: string;
  status: 'Pending' | 'Published' | 'Rejected';
  createdAt: Date;
  engagementPrediction?: string;
}

@Component({
  selector: 'app-content',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './content.html',
  styleUrl: './content.css',
})
export class Content {
  contentItems: ContentItem[] = [
    {
      id: 'c1',
      platform: 'Twitter',
      content: 'Just deployed the new ZeroClaw Mission Control OS! The future of autonomous AI swarms is here. 🚀 #AI #ZeroClaw #BuildInPublic',
      authorAgent: 'TechWriter',
      status: 'Pending',
      createdAt: new Date(Date.now() - 1000 * 60 * 30),
      engagementPrediction: 'High'
    },
    {
      id: 'c2',
      platform: 'LinkedIn',
      content: 'Reflecting on the architecture of multi-agent systems. The coordination between our Architect, QA, and DevOps agents has reduced deployment times by 40%. Full write-up coming soon on the engineering blog.',
      authorAgent: 'Architect',
      status: 'Pending',
      createdAt: new Date(Date.now() - 1000 * 60 * 120)
    },
    {
      id: 'c3',
      platform: 'Blog',
      content: 'Title: Implementing Sovereign Ledgers in AI Orgs\n\nAbstract: How we built a secure, append-only ledger for AI treasury management using local JSONL datastores and the Boardroom Analyst skill...',
      authorAgent: 'Researcher',
      status: 'Pending',
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 5)
    },
    {
      id: 'c4',
      platform: 'Twitter',
      content: 'The gemini-expert subagent is officially live and executing shell commands on command! ⚡️',
      authorAgent: 'TechWriter',
      status: 'Published',
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24)
    }
  ];

  get pendingCount() {
    return this.contentItems.filter(item => item.status === 'Pending').length;
  }

  get publishedCount() {
    return this.contentItems.filter(item => item.status === 'Published').length;
  }

  approveItem(id: string) {
    const item = this.contentItems.find(i => i.id === id);
    if (item) item.status = 'Published';
  }

  rejectItem(id: string) {
    const item = this.contentItems.find(i => i.id === id);
    if (item) item.status = 'Rejected';
  }
}
