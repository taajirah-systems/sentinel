import { Component, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

interface CouncilMessage {
  id: string;
  agentName: string;
  agentRole: string;
  avatar: string;
  content: string;
  timestamp: Date;
  type: 'message' | 'system' | 'action';
  color: string;
}

@Component({
  selector: 'app-council',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './council.html',
  styleUrl: './council.css',
})
export class Council {
  private zeroclaw = inject(Zeroclaw);

  activeSessionContext = 'Real-time Swarm Feed';

  messages = computed(() => {
    const rawLogs = this.zeroclaw.logs();
    const parsed: CouncilMessage[] = [];

    rawLogs.forEach((log, i) => {
      const msgText = log.message || '';

      // Basic heuristic to parse meaning from the log text
      if (msgText.includes('💬 [telegram]')) {
        parsed.push({
          id: `log-${i}`,
          agentName: 'User',
          agentRole: 'External Input',
          avatar: '👤',
          content: msgText.split('from')[1]?.trim() || msgText,
          timestamp: new Date(log.timestamp || Date.now()),
          type: 'message',
          color: 'text-gray-200'
        });
      } else if (msgText.includes('🤖 Reply')) {
        parsed.push({
          id: `log-${i}`,
          agentName: 'ZeroClaw',
          agentRole: 'Agent Response',
          avatar: '🤖',
          content: msgText.replace(/🤖 Reply \(\d+ms\):/, '').trim(),
          timestamp: new Date(log.timestamp || Date.now()),
          type: 'message',
          color: 'text-emerald-400'
        });
      } else if (msgText.includes('WARN zeroclaw')) {
        parsed.push({
          id: `log-${i}`,
          agentName: 'System',
          agentRole: 'Warning',
          avatar: '⚠️',
          content: msgText.split('WARN')[1]?.trim() || msgText,
          timestamp: new Date(log.timestamp || Date.now()),
          type: 'action',
          color: 'text-orange-400'
        });
      } else if (msgText.includes('INFO zeroclaw')) {
        parsed.push({
          id: `log-${i}`,
          agentName: 'System',
          agentRole: 'Info',
          avatar: 'ℹ️',
          content: msgText.split('INFO')[1]?.trim() || msgText,
          timestamp: new Date(log.timestamp || Date.now()),
          type: 'system',
          color: 'text-blue-400'
        });
      } else if (msgText.trim().length > 0) {
        // Generic system/action log
        parsed.push({
          id: `log-${i}`,
          agentName: 'Daemon',
          agentRole: 'Process Event',
          avatar: '⚙️',
          content: msgText.replace(/\[\dm/g, '').trim(), // strip ansi loosely
          timestamp: new Date(log.timestamp || Date.now()),
          type: 'system',
          color: 'text-gray-500'
        });
      }
    });

    // Show the last 100 log items
    return parsed.slice(-100);
  });
}
