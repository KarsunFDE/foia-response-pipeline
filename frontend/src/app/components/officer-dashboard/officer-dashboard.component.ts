import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { RoleService } from '../../services/role.service';
import { FIXTURE_SOLICITATIONS } from '../../services/mock-fixtures';
import { NotificationService } from '../../services/notification.service';

/**
 * FOIA Officer Dashboard — role-aware landing for FOIA Officer / General
 * Counsel / Records Custodian.
 *
 * KPI tiles for the FOIA pipeline: requests in intake, exemption-analysis
 * backlog, requests AT STATUTORY RISK (≤5 working days), awaiting HITL
 * release, and open appeals. The 20-working-day clock is front-and-centre.
 * Touches Item 8 (hardcoded URL lives in the foiaRequest-list component
 * referenced below) — keeping the localized teaching artifact intact.
 */
@Component({
  selector: 'app-officer-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-header">
      <div>
        <h2>{{ greeting() }}</h2>
        <div class="subtitle">{{ role.current.displayName }} · {{ role.current.authorityNote }}</div>
      </div>
      <div>
        <a routerLink="/foiaRequests/new"><button>+ New FOIA request</button></a>
      </div>
    </div>

    <section class="kpi-grid">
      <div class="kpi-tile">
        <div class="kpi-value">{{ inIntake() }}</div>
        <div class="kpi-label">In intake triage</div>
      </div>
      <div class="kpi-tile">
        <div class="kpi-value">{{ exemptionBacklog() }}</div>
        <div class="kpi-label">Exemption-analysis backlog</div>
      </div>
      <div class="kpi-tile" style="border-left-color: var(--color-accent)">
        <div class="kpi-value">{{ atStatutoryRisk() }}</div>
        <div class="kpi-label">⏱ At statutory risk (≤ 5 wd)</div>
      </div>
      <div class="kpi-tile">
        <div class="kpi-value">{{ awaitingRelease() }}</div>
        <div class="kpi-label">Awaiting HITL release</div>
      </div>
      <div class="kpi-tile">
        <div class="kpi-value">{{ openAppeals() }}</div>
        <div class="kpi-label">Open appeals</div>
      </div>
    </section>

    <div class="two-col">
      <div class="card">
        <h3>Request pipeline (20-working-day clock)</h3>
        <table>
          <thead><tr><th>Request</th><th>State</th><th>Due</th></tr></thead>
          <tbody>
            <tr *ngFor="let s of pipeline()">
              <td>
                <a [routerLink]="['/foiaRequests', s.id, 'edit']">{{ s.title }}</a>
                <div style="font-size:0.75rem;color:var(--color-fg-muted)">{{ s.trackingNumber }} · {{ s.requesterType }}</div>
              </td>
              <td><span class="badge" [ngClass]="(s.status || '').toLowerCase()">{{ s.status }}</span></td>
              <td [style.color]="workingDaysLeft(s.dueDate) !== null && workingDaysLeft(s.dueDate)! <= 5 ? 'var(--color-accent-dark)' : ''">
                {{ dueDisplay(s.dueDate) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h3>Recent activity</h3>
        <ul>
          <li *ngFor="let n of recent()">
            <strong>{{ n.title }}</strong>
            <div style="font-size:0.85rem;color:var(--color-fg-muted)">{{ n.body }} · {{ n.createdAt | date:'short' }}</div>
          </li>
        </ul>
      </div>
    </div>

    <div class="card" style="margin-top:1rem">
      <h3>Quick links</h3>
      <p>
        <a routerLink="/foiaRequests">All FOIA requests</a> ·
        <a routerLink="/reports">All reports</a> ·
        <a routerLink="/admin/audit">Audit log search</a>
      </p>
      <p style="font-size:0.8rem;color:var(--color-fg-muted)">
        ⚠ Legacy foiaRequest-list (Debt Item 8) is still wired at
        <a routerLink="/foiaRequests">/foiaRequests</a> — preserved
        as the W4 Tue API-modernization teaching artifact.
      </p>
    </div>
  `,
})
export class OfficerDashboardComponent {
  constructor(public role: RoleService, private notif: NotificationService) {}

  greeting(): string {
    const hour = new Date().getHours();
    const time = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
    return `${time}, ${this.role.current.displayName.split(' ')[0]}`;
  }

  /** Working days until `dueDate` (negative = overdue); null if unset. */
  workingDaysLeft(dueDate?: string): number | null {
    if (!dueDate) return null;
    const due = new Date(dueDate);
    const now = new Date();
    let days = 0;
    const cursor = new Date(now);
    while (cursor < due) {
      cursor.setDate(cursor.getDate() + 1);
      const d = cursor.getDay();
      if (d !== 0 && d !== 6) days++;
    }
    return due < now ? -days : days;
  }

  dueDisplay(dueDate?: string): string {
    const n = this.workingDaysLeft(dueDate);
    if (n === null) return '—';
    if (n < 0) return `${-n} wd OVERDUE`;
    return `${n} wd`;
  }

  inIntake(): number {
    return FIXTURE_SOLICITATIONS.filter((s) => s.status === 'INTAKE_TRIAGE').length;
  }

  exemptionBacklog(): number {
    return FIXTURE_SOLICITATIONS.filter((s) =>
      ['EXEMPTION_ANALYSIS', 'REDACTION_PROPOSAL'].includes(s.status as string),
    ).length;
  }

  atStatutoryRisk(): number {
    return FIXTURE_SOLICITATIONS.filter((s) => {
      const n = this.workingDaysLeft(s.dueDate);
      return n !== null && n <= 5;
    }).length;
  }

  awaitingRelease(): number {
    return FIXTURE_SOLICITATIONS.filter((s) => s.status === 'HITL_REVIEW').length;
  }

  openAppeals(): number {
    return FIXTURE_SOLICITATIONS.filter((s) => s.status === 'APPEAL').length;
  }

  pipeline() {
    return FIXTURE_SOLICITATIONS.slice(0, 4);
  }

  recent() {
    // Read once from the notification service cache.
    let cache: any[] = [];
    this.notif.items$.subscribe((items) => (cache = items)).unsubscribe();
    return cache.slice(0, 4);
  }
}
