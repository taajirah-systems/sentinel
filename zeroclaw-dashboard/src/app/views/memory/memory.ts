import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface MemoryItem {
  id: string;
  name: string;
  type: 'folder' | 'file';
  size?: string;
  date: string;
  content?: string;
  icon?: string;
}

@Component({
  selector: 'app-memory',
  imports: [CommonModule],
  templateUrl: './memory.html',
  styleUrl: './memory.css',
  standalone: true
})
export class Memory {
  activeFile: MemoryItem | null = null;

  memoryItems: MemoryItem[] = [
    { id: '1', name: 'System Context', type: 'folder', date: 'Mar 01' },
    { id: '2', name: 'core_directives.md', type: 'file', size: '12 KB', date: 'Mar 01', icon: 'file-text', content: '# Mission Control Directives\n\n1. Maintain absolute sovereign control over the ledger.\n2. Execute SWARM protocols on trigger.\n3. Ensure agents adhere to their system prompts.\n\n---\n\n## Network Rules\nAll inbound and outbound hooks must be verifiable.\nFail-over model: gemini-2.5-pro -> claude-3-opus' },
    { id: '3', name: 'agent_profiles.json', type: 'file', size: '4 KB', date: 'Mar 02', icon: 'code', content: '{\n  "architect": {\n    "role": "System Design",\n    "model": "gemini-2.5-pro"\n  },\n  "coder": {\n    "role": "Implementation",\n    "model": "gemini-2.5-flash"\n  }\n}' },
    { id: '4', name: 'Learned Experiences', type: 'folder', date: 'Mar 03' },
    { id: '5', name: 'api_integration_notes.txt', type: 'file', size: '8 KB', date: 'Mar 03', icon: 'file-text', content: 'Firecrawl API successfully integrated...\nRate limits observed at 100 req/min.\nAuthentication via bearer token in headers.\n\nTODO: implement backoff retry loop.' }
  ];

  selectFile(item: MemoryItem) {
    if (item.type === 'file') {
      this.activeFile = item;
    } else {
      // Ignore folder click for now
      this.activeFile = null;
    }
  }
}
