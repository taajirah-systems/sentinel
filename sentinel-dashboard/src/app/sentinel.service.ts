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
        return this.http.get<AuditLog[]>(`${this.apiUrl}/logs`, { headers: this.getHeaders() }).pipe(
            map(logs => logs.map(log => ({
                ...log,
                timestamp: this.formatDate(log.timestamp)
            }))),
            catchError(() => of([]))
        );
    }

    private formatDate(timestamp: any): string {
        if (!timestamp) return 'Unknown';
        const date = new Date(typeof timestamp === 'number' ? timestamp * 1000 : timestamp);
        return date.toLocaleString();
    }
}
