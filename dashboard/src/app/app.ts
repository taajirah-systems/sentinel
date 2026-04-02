import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class AppComponent implements OnInit {
  activeTab: string = 'overview';
  
  // Data State
  wallets: any[] = [];
  complianceWallets: any[] = [];
  approvalsHistory: any[] = [];
  spendAnalytics: any = null;
  oracleData: any = null;
  
  exceptions: any[] = [];
  walletHierarchy: any[] = [];
  selectedHold: any = null;
  
  // Forms
  allocationRecipient: string = '';
  allocationAmount: number = 0;
  allocationReference: string = '';
  
  resolutionNotes: string = '';
  
  apiUrl = 'http://localhost:8765/api/admin';

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  get httpAuth() {
    return { headers: { 'x-sentinel-token': 'f6acf84a8aeaf8abebae9a13700671d34c7bcaa7c8705971d0f61a9790f9b590' } };
  }

  ngOnInit() {
    this.fetchData();
    setInterval(() => this.fetchData(), 5000);
  }

  fetchData() {
    // 1. Wallets & Compliance
    this.http.get<any>(`${this.apiUrl}/wallets`, this.httpAuth).subscribe(res => {
      this.wallets = Object.keys(res.wallets).map(k => ({ id: k, ...res.wallets[k] }));
      this.cdr.detectChanges();
    });

    this.http.get<any>(`${this.apiUrl}/wallets/compliance`, this.httpAuth).subscribe(res => {
      this.complianceWallets = Object.keys(res.contractors).map(k => ({ id: k, ...res.contractors[k] }));
      this.cdr.detectChanges();
    });

    // 2. Governance History
    this.http.get<any>(`${this.apiUrl}/governance/history`, this.httpAuth).subscribe(res => {
      this.approvalsHistory = res.history;
      this.cdr.detectChanges();
    });

    // 3. Spend Analytics
    this.http.get<any>(`${this.apiUrl}/analytics/spend`, this.httpAuth).subscribe(res => {
      this.spendAnalytics = res;
      this.cdr.detectChanges();
    });

    // 4. Oracle
    this.http.get<any>(`${this.apiUrl}/oracle`, this.httpAuth).subscribe(res => {
      this.oracleData = res;
      this.cdr.detectChanges();
    });

    // 5. Exceptions & Hierarchy
    this.http.get<any>(`${this.apiUrl}/integrity/exceptions`, this.httpAuth).subscribe(res => {
      this.exceptions = res.events;
      this.cdr.detectChanges();
    });

    this.http.get<any>(`${this.apiUrl}/wallets/hierarchy`, this.httpAuth).subscribe(res => {
      this.walletHierarchy = res.hierarchy;
      this.cdr.detectChanges();
    });
  }

  setTab(tab: string) {
    this.activeTab = tab;
    this.fetchData();
  }

  resolveApproval(reqId: string, decision: 'APPROVE' | 'DENY') {
    const notes = prompt(`Resolution Reason for ${reqId}:`, "Admin decision");
    if (notes === null) return;

    const payload = { request_id: reqId, decision, actor_id: 'admin_dashboard', notes };
    this.http.post<any>(`${this.apiUrl}/governance/resolve`, payload, this.httpAuth).subscribe(res => {
       this.fetchData();
    });
  }

  submitAllocation() {
    if(!this.allocationRecipient || this.allocationAmount <= 0) return;
    const payload = { recipient: this.allocationRecipient, amount_jul: this.allocationAmount, reference: this.allocationReference };
    this.http.post<any>(`${this.apiUrl}/treasury/allocate`, payload, this.httpAuth).subscribe(res => {
       alert(`Successfully allocated ${this.allocationAmount} JOULE credits.`);
       this.allocationRecipient = '';
       this.allocationAmount = 0;
       this.allocationReference = '';
       this.fetchData();
    }, err => alert('Allocation Error: ' + (err.error?.detail || err.message)));
  }

  resolveHold(holdId: string, action: string) {
    const reason = prompt(`Audit Reason for manual ${action}:`, "Manual administrative resolution");
    if (reason === null) return;

    this.http.post<any>(`${this.apiUrl}/holds/${holdId}/resolve?resolution_action=${action}&audit_reason=${reason}`, {}, this.httpAuth).subscribe(res => {
       alert(`Hold ${holdId} resolved via ${action}`);
       this.fetchData();
    }, err => alert('Resolution Error: ' + (err.error?.detail || err.message)));
  }

  get pendingCount() {
    return this.approvalsHistory.filter(h => h.status === 'pending').length;
  }
}
