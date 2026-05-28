import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FoiaRequest } from '../../models/foia-request';

/**
 * FoiaRequest list view.
 *
 * ⚠ DELIBERATE BROWNFIELD DEBT — Item 8 in docs/brownfield-debt.md ⚠
 *
 * This component hardcodes `http://localhost:8081/api/foia-requests` —
 * bypassing the API gateway at :8080. Compare with
 * {@link ../../services/foia-request.service.ts} which uses
 * `environment.apiGatewayUrl`.
 *
 * The hardcode was introduced "temporarily" by a developer who couldn't
 * get the gateway running locally and was never reverted. Cohort fixes
 * in W4 Tue API modernization patterns.
 */
@Component({
  selector: 'app-foiaRequest-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <h2>FOIA requests</h2>
    <p>
      <a routerLink="/foiaRequests/new"><button>+ New FOIA request</button></a>
    </p>
    <div *ngIf="loading">Loading…</div>
    <div *ngIf="error" style="color: crimson">{{ error }}</div>
    <table *ngIf="!loading && !error">
      <thead>
        <tr><th>Subject</th><th>Agency</th><th>Status</th><th>Tracking #</th></tr>
      </thead>
      <tbody>
        <tr *ngFor="let s of foiaRequests">
          <td>{{ s.title }}</td>
          <td>{{ s.agencyId }}</td>
          <td>{{ s.status }}</td>
          <td><code>{{ s.trackingNumber || s.id }}</code></td>
        </tr>
        <tr *ngIf="foiaRequests.length === 0">
          <td colspan="4"><em>No FOIA requests yet. Create one!</em></td>
        </tr>
      </tbody>
    </table>
  `,
})
export class FoiaRequestListComponent implements OnInit {
  // ⚠ Item 8 — hardcoded URL bypasses the API gateway at :8080.
  private apiUrl = 'http://localhost:8081/api/foia-requests';

  foiaRequests: FoiaRequest[] = [];
  loading = true;
  error: string | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.http.get<FoiaRequest[]>(this.apiUrl).subscribe({
      next: (data) => {
        this.foiaRequests = data || [];
        this.loading = false;
      },
      error: (err) => {
        this.error = `Failed to load foiaRequests: ${err.message ?? err}`;
        this.loading = false;
      },
    });
  }
}
