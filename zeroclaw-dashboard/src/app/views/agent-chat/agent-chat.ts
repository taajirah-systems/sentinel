import { Component, inject, signal, ViewChild, ElementRef, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Zeroclaw } from '../../services/zeroclaw';

interface ChatMessage {
  role: 'user' | 'agent';
  content: string;
  timestamp: Date;
}

@Component({
  selector: 'app-agent-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './agent-chat.html',
  styleUrl: './agent-chat.css',
})
export class AgentChat implements OnInit {
  private zeroclaw = inject(Zeroclaw);
  private route = inject(ActivatedRoute);

  @ViewChild('messagesEnd') messagesEnd!: ElementRef;

  selectedAgent = signal<string | null>(null);

  messages = signal<ChatMessage[]>([
    {
      role: 'agent',
      content: 'ZeroClaw online. How can I serve you, Commander?',
      timestamp: new Date()
    }
  ]);

  input = '';
  isSending = signal(false);

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      const agentName = params['agent'];
      if (agentName) {
        this.selectedAgent.set(agentName);
        this.messages.update(m => [...m, {
          role: 'agent',
          content: `Connecting you to ${agentName}. What do you need?`,
          timestamp: new Date()
        }]);
      }
    });
  }

  async send() {
    const text = this.input.trim();
    if (!text || this.isSending()) return;

    this.messages.update(m => [...m, { role: 'user', content: text, timestamp: new Date() }]);
    this.input = '';
    this.isSending.set(true);

    try {
      const result = await this.zeroclaw.sendMessage(text);
      const reply = result?.reply || result?.response || result?.message || 'Acknowledged.';
      this.messages.update(m => [...m, { role: 'agent', content: reply, timestamp: new Date() }]);
    } catch {
      this.messages.update(m => [...m, {
        role: 'agent', content: '⚠️ Failed to reach ZeroClaw daemon. Check connection.', timestamp: new Date()
      }]);
    } finally {
      this.isSending.set(false);
      setTimeout(() => this.messagesEnd?.nativeElement?.scrollIntoView({ behavior: 'smooth' }), 50);
    }
  }

  onKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }

  formatTime(d: Date): string {
    return d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' });
  }
}
