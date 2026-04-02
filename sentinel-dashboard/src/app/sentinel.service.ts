import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

export interface PendingRequest {
    id: string;
    command: string;
    reason: string;
    status: string;
    timestamp: string;
}

export interface AuditLog {
    command: string;
    allowed: boolean;
    timestamp: string;
    risk_score?: number;
    reason?: string;
}

@Injectable({
    providedIn: 'root'
})
export class SentinelService {
    private apiUrl = window.location.origin; // Absolute path to same origin

    constructor(private http: HttpClient) { }

    private getHeaders(): HttpHeaders {
        const token = localStorage.getItem('sentinel_token') || '';
        return new HttpHeaders({
            'Content-Type': 'application/json',
            'X-Sentinel-Token': token
        });
    }

    checkHealth(): Observable<boolean> {
        return this.http.get<{ status: string }>(`${this.apiUrl}/health`).pipe(
            map(res => res.status === 'healthy'),
            catchError(() => of(false))
        );
    }

    getPendingRequests(): Observable<PendingRequest[]> {
        return this.http.get<{ [key: string]: PendingRequest }>(`${this.apiUrl}/pending`, { headers: this.getHeaders() }).pipe(
            map(data => Object.values(data))
        );
    }

    approveRequest(id: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/approve/${id}`, {}, { headers: this.getHeaders() });
    }

    getAuditLogs(): Observable<AuditLog[]> {
        return this.http.get<{ requests: any[] }>(`${this.apiUrl}/api/admin/governance/requests`, { headers: this.getHeaders() }).pipe(
            map(res => res.requests),
            catchError(() => of([]))
        );
    }

    getActiveHolds(): Observable<any[]> {
        return this.http.get<{ holds: any[] }>(`${this.apiUrl}/api/admin/holds/active`, { headers: this.getHeaders() }).pipe(
            map(res => res.holds),
            catchError(() => of([]))
        );
    }

    getHoldHistory(): Observable<any[]> {
        return this.http.get<{ history: any[] }>(`${this.apiUrl}/api/admin/holds/history`, { headers: this.getHeaders() }).pipe(
            map(res => res.history),
            catchError(() => of([]))
        );
    }

    getComplianceShortfalls(): Observable<any[]> {
        return this.http.get<{ events: any[] }>(`${this.apiUrl}/api/admin/compliance/shortfalls`, { headers: this.getHeaders() }).pipe(
            map(res => res.events),
            catchError(() => of([]))
        );
    }

    getWallets(): Observable<any> {
        return this.http.get<{ wallets: any }>(`${this.apiUrl}/api/admin/wallets`, { headers: this.getHeaders() }).pipe(
            map(res => res.wallets),
            catchError(() => of({}))
        );
    }

    private formatDate(timestamp: any): string {
        if (!timestamp) return 'Unknown';
        const date = new Date(typeof timestamp === 'number' ? timestamp * 1000 : timestamp);
        return date.toLocaleString();
    }
}
