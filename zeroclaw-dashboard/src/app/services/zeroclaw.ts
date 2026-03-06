import { Injectable, signal } from '@angular/core';

export interface LogEvent {
  type?: string;
  source?: string;
  data?: any;
  timestamp?: string;
  message?: string;
  [key: string]: any;
}

@Injectable({
  providedIn: 'root',
})
export class Zeroclaw {
  private eventSource: EventSource | null = null;

  // Public reactive state
  public logs = signal<LogEvent[]>([]);
  public isConnected = signal<boolean>(false);

  constructor() {
    this.connect();
  }

  private async connect() {
    console.log('Attempting ZeroClaw SSE connection with fetch...');
    try {
      const response = await fetch('/api/logs', {
        headers: { Accept: 'text/event-stream' }
      });

      if (!response.ok || !response.body) {
        throw new Error(`Failed to connect: ${response.status}`);
      }

      this.isConnected.set(true);
      console.log('ZeroClaw SSE connected via fetch');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const dataString = line.substring(6).trim();
              if (dataString === '[DONE]' || !dataString) continue;

              const parsed = JSON.parse(dataString);
              console.log('SSE raw data:', parsed);
              this.logs.update((current) => [...current, parsed]);
            } catch (err) {
              console.error('JSON parse error for SSE data line:', line, err);
            }
          }
        }
      }
    } catch (error) {
      console.error('ZeroClaw SSE fetch error', error);
      this.isConnected.set(false);
    } finally {
      // Auto-reconnect after 3 seconds
      setTimeout(() => this.connect(), 3000);
    }
  }

  /** Send a message to the ZeroClaw agent */
  public async sendMessage(message: string) {
    try {
      const response = await fetch('/api/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to send message', error);
      throw error;
    }
  }

  /** Fetch all tasks */
  public async getTasks() {
    try {
      const response = await fetch('/api/tasks');
      if (!response.ok) throw new Error('Failed to fetch tasks');
      return await response.json();
    } catch (error) {
      console.error('getTasks error:', error);
      return [];
    }
  }

  /** Update all tasks */
  public async updateTasks(tasks: any[]) {
    try {
      const response = await fetch('/api/tasks', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tasks),
      });
      if (!response.ok) throw new Error('Failed to update tasks');
      return await response.json();
    } catch (error) {
      console.error('updateTasks error:', error);
      throw error;
    }
  }

  /** Fetch all agents from ZeroClaw */
  public async getAgents() {
    try {
      const response = await fetch('/api/agents');
      if (!response.ok) throw new Error('Failed to fetch agents');
      return await response.json();
    } catch (error) {
      console.error('getAgents error:', error);
      return [];
    }
  }

  /** Fetch live system metrics (CPU, memory, disk, network, uptime) */
  public async getMetrics() {
    try {
      const response = await fetch('/api/metrics');
      if (!response.ok) throw new Error('Failed to fetch metrics');
      return await response.json();
    } catch (error) {
      console.error('getMetrics error:', error);
      return null;
    }
  }

  /** Fetch live OS process list */
  public async getProcesses() {
    try {
      const response = await fetch('/api/processes');
      if (!response.ok) throw new Error('Failed to fetch processes');
      return await response.json();
    } catch (error) {
      console.error('getProcesses error:', error);
      return [];
    }
  }

  /** Fetch factory pipelines */
  public async getPipelines() {
    try {
      const response = await fetch('/api/pipelines');
      if (!response.ok) throw new Error('Failed to fetch pipelines');
      return await response.json();
    } catch (error) {
      console.error('getPipelines error:', error);
      return [];
    }
  }

  /** Fetch treasury ledger entries */
  public async getLedger() {
    try {
      const response = await fetch('/api/ledger');
      if (!response.ok) throw new Error('Failed to fetch ledger');
      return await response.json();
    } catch (error) {
      console.error('getLedger error:', error);
      return [];
    }
  }

  /** Fetch active workspaces */
  public async getWorkspaces() {
    try {
      const response = await fetch('/api/workspaces');
      if (!response.ok) throw new Error('Failed to fetch workspaces');
      return await response.json();
    } catch (error) {
      console.error('getWorkspaces error:', error);
      return [];
    }
  }

  /** Fetch radar/intelligence signals */
  public async getRadarSignals() {
    try {
      const response = await fetch('/api/radar');
      if (!response.ok) throw new Error('Failed to fetch radar signals');
      return await response.json();
    } catch (error) {
      console.error('getRadarSignals error:', error);
      return { signals: [], trends: [], activeSignals: 0, processedToday: 0 };
    }
  }

  /** Fetch people / team members */
  public async getPeople() {
    try {
      const response = await fetch('/api/people');
      if (!response.ok) throw new Error('Failed to fetch people');
      return await response.json();
    } catch (error) {
      console.error('getPeople error:', error);
      return [];
    }
  }

  /** Fetch pending authorization requests */
  public async getAuthRequests() {
    try {
      const response = await fetch('/api/auth-requests');
      if (!response.ok) throw new Error('Failed to fetch auth requests');
      return await response.json();
    } catch (error) {
      console.error('getAuthRequests error:', error);
      return [];
    }
  }

  /** Approve or reject an authorization request */
  public async resolveAuthRequest(id: string, action: 'approve' | 'reject') {
    try {
      const response = await fetch(`/api/auth-requests/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      if (!response.ok) throw new Error(`Failed to ${action} request`);
      return await response.json();
    } catch (error) {
      console.error('resolveAuthRequest error:', error);
      throw error;
    }
  }

  /** Spawn a new ZeroClaw agent */
  public async spawnAgent(name?: string) {
    try {
      const response = await fetch('/api/spawn-agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (!response.ok) throw new Error('Failed to spawn agent');
      return await response.json();
    } catch (error) {
      console.error('spawnAgent error:', error);
      throw error;
    }
  }
}
