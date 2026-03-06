import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface DocItem {
  id: string;
  title: string;
  category: string;
  lastEdited: string;
  author: string;
  content: string;
  tags: string[];
}

@Component({
  selector: 'app-docs',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './docs.html',
  styleUrl: './docs.css',
})
export class Docs {
  public categories = ['All Docs', 'Technical', 'Business', 'Vision', 'Research'];
  public activeCategory = 'All Docs';

  public docItems: DocItem[] = [
    {
      id: 'DOC-001',
      title: 'Mission Control: OS Architecture',
      category: 'Technical',
      lastEdited: '2 hours ago',
      author: 'Architect',
      tags: ['Angular', 'OS-Design'],
      content: 'The core architecture follows a 3-column obsidian-inspired layout using real-time SSE streams...'
    },
    {
      id: 'DOC-002',
      title: 'Sovereign Ledger PRD',
      category: 'Business',
      lastEdited: '5 hours ago',
      author: 'Strategist',
      tags: ['Ledger', 'Economy'],
      content: 'A detailed breakdown of the sovereign treasury system and ledger-based tracking of inflows and outflows...'
    },
    {
      id: 'DOC-003',
      title: 'Agent Autonomy Guidelines',
      category: 'Vision',
      lastEdited: '1 day ago',
      author: 'Henry',
      tags: ['AI-Safety', 'Policy'],
      content: 'Core principles governing how Zeroclaw agents interact with external APIs and make autonomous decisions...'
    },
    {
      id: 'DOC-004',
      title: 'Quantum Sentiment Analysis',
      category: 'Research',
      lastEdited: '3 days ago',
      author: 'Researcher',
      tags: ['Web3', 'Sentiment'],
      content: 'Exploring the potential for quantum-assisted sentiment analysis in real-time market signals...'
    }
  ];

  public selectedDoc: DocItem | null = this.docItems[0];

  selectDoc(doc: DocItem) {
    this.selectedDoc = doc;
  }

  setCategory(cat: string) {
    this.activeCategory = cat;
  }

  get filteredDocs() {
    if (this.activeCategory === 'All Docs') return this.docItems;
    return this.docItems.filter(doc => doc.category === this.activeCategory);
  }
}
