import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

interface LedgerEntry {
  timestamp: string;
  transaction_id: string;
  type: 'Inflow' | 'Outflow';
  amount_zar: number;
  description: string;
  entity: string;
}

@Component({
  selector: 'app-treasury',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './treasury.html',
  styleUrl: './treasury.css',
})
export class Treasury implements OnInit {
  private zeroclaw = inject(Zeroclaw);

  ledger = signal<LedgerEntry[]>([]);
  loading = signal(true);

  totalInflow = computed(() =>
    this.ledger().filter(e => e.type === 'Inflow').reduce((s, e) => s + e.amount_zar, 0)
  );
  totalOutflow = computed(() =>
    this.ledger().filter(e => e.type === 'Outflow').reduce((s, e) => s + e.amount_zar, 0)
  );
  balance = computed(() => this.totalInflow() - this.totalOutflow());

  async ngOnInit() {
    const data = await this.zeroclaw.getLedger();
    if (data?.length) this.ledger.set(data);
    this.loading.set(false);
  }

  formatZAR(amount: number): string {
    return `R ${amount.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  formatDate(ts: string): string {
    return new Date(ts).toLocaleDateString('en-ZA', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  }
}
