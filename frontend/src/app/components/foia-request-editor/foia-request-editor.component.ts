import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FoiaRequest, FOIA_EXEMPTIONS } from '../../models/foia-request';
import { FIXTURE_SOLICITATIONS } from '../../services/mock-fixtures';

/**
 * FOIA request workspace — exemption analysis + redaction proposal for a
 * request under processing.
 *
 * Includes a side-panel precedent lookup (RAG over 5 USC 552 / 28 CFR 16),
 * which is the W2 anchor surface (hybrid lexical + vector). The search input
 * here is the W2 Wed retrieval-boundary work surface — must filter by
 * agency_id (Item 10).
 */
@Component({
  selector: 'app-foiaRequest-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page-header">
      <div>
        <h2>{{ foiaRequest?.title || 'FOIA request' }}</h2>
        <div class="subtitle">
          <span class="badge" [ngClass]="(foiaRequest?.status || 'intake_triage').toLowerCase()">{{ foiaRequest?.status }}</span>
          · {{ foiaRequest?.trackingNumber }} · {{ foiaRequest?.requesterType }}
          <span class="due-pill" [class.at-risk]="dueDaysLeft() !== null && dueDaysLeft()! <= 5">
            ⏱ {{ dueLabel() }}
          </span>
        </div>
      </div>
      <div>
        <a [routerLink]="['/foiaRequests', id, 'amendments']"><button class="secondary">Determinations</button></a>
        <a [routerLink]="['/foiaRequests', id, 'qa']"><button class="secondary">Requester correspondence</button></a>
        <a [routerLink]="['/redaction-review', id, 'consensus']"><button class="secondary">Redaction review</button></a>
      </div>
    </div>

    <div class="two-col">
      <div>
        <div class="card">
          <h3>Records sought</h3>
          <textarea rows="5" [(ngModel)]="recordsSought"></textarea>
        </div>
        <div class="card">
          <h3>Exemption analysis (5 USC 552(b))</h3>
          <p style="font-size:0.8rem;color:var(--color-fg-muted)">
            Tag the responsive material with the applicable exemption(s) and
            record the basis. AI-assist proposes exemptions via
            <code>POST /analyze-exemptions</code> (W2).
          </p>
          <label *ngFor="let ex of exemptions" style="display:flex;gap:0.5rem;align-items:flex-start;margin-bottom:0.35rem">
            <input type="checkbox" [(ngModel)]="claimed[ex.code]" style="width:auto;margin-top:0.2rem"/>
            <span style="font-size:0.85rem">{{ ex.label }}</span>
          </label>
        </div>
        <div class="card">
          <h3>Redaction rationale</h3>
          <textarea rows="5" [(ngModel)]="rationale"
                    placeholder="Why each segment is withheld (deliberative / privacy / law-enforcement basis)…"></textarea>
        </div>
      </div>

      <div>
        <div class="card">
          <h3>FOIA precedent (RAG)</h3>
          <p style="font-size:0.8rem;color:var(--color-fg-muted)">
            Hybrid lexical + Atlas Vector Search over 5 USC 552 / 28 CFR 16.
            <em>Filtered by agency_id — Item 10 surface.</em>
          </p>
          <input [(ngModel)]="precedentQuery" (keyup.enter)="searchPrecedent()" placeholder="e.g., deliberative process (b)(5)"/>
          <button (click)="searchPrecedent()" style="margin-top:0.5rem">Search</button>
          <ul *ngIf="precedentResults.length > 0">
            <li *ngFor="let c of precedentResults">
              <strong>{{ c.id }}</strong> — {{ c.title }}
              <button class="secondary" style="font-size:0.75rem;padding:0.1rem 0.35rem">Cite</button>
            </li>
          </ul>
        </div>

        <div class="card">
          <h3>State transition</h3>
          <select [(ngModel)]="targetState">
            <option value="INTAKE_TRIAGE">INTAKE_TRIAGE</option>
            <option value="EXEMPTION_ANALYSIS">EXEMPTION_ANALYSIS</option>
            <option value="REDACTION_PROPOSAL">REDACTION_PROPOSAL</option>
            <option value="HITL_REVIEW">HITL_REVIEW (GC review)</option>
            <option value="RESPONSE">RESPONSE (release/withhold)</option>
            <option value="APPEAL">APPEAL</option>
          </select>
          <button style="margin-top:0.5rem">Transition</button>
          <p style="font-size:0.75rem;color:var(--color-fg-muted);margin-top:0.5rem">
            ⚠ Transitions audit-logged (Item 2 race surface).
          </p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .due-pill { margin-left:0.5rem; padding:0.05rem 0.5rem; border-radius:999px;
      font-size:0.72rem; background:#eef; color:var(--color-fg-muted); }
    .due-pill.at-risk { background:#fde8d3; color:var(--color-accent-dark); font-weight:700; }
  `],
})
export class FoiaRequestEditorComponent implements OnInit {
  id = '';
  foiaRequest: FoiaRequest | null = null;
  recordsSought = '';
  rationale = '';
  precedentQuery = '';
  precedentResults: { id: string; title: string }[] = [];
  targetState = 'EXEMPTION_ANALYSIS';
  exemptions = FOIA_EXEMPTIONS;
  claimed: Record<string, boolean> = {};

  constructor(private route: ActivatedRoute) {}

  ngOnInit(): void {
    this.id = this.route.snapshot.params['id'];
    this.foiaRequest = FIXTURE_SOLICITATIONS.find((s) => s.id === this.id)
      ?? FIXTURE_SOLICITATIONS[0];
    this.recordsSought = this.foiaRequest.recordsSought ?? '';
  }

  /** Working days until the statutory due date (null if no due date). */
  dueDaysLeft(): number | null {
    if (!this.foiaRequest?.dueDate) return null;
    const due = new Date(this.foiaRequest.dueDate);
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

  dueLabel(): string {
    const n = this.dueDaysLeft();
    if (n === null) return 'no due date';
    if (n < 0) return `${-n} working days OVERDUE`;
    return `${n} working days to statutory due date`;
  }

  searchPrecedent(): void {
    // Stub — in W2, hits POST /rag/clause-search over the FOIA precedent corpus.
    const q = this.precedentQuery.toLowerCase();
    this.precedentResults = [
      { id: '5 USC 552(b)(5)', title: 'Deliberative-process privilege' },
      { id: '5 USC 552(b)(6)', title: 'Personal-privacy balancing' },
      { id: '28 CFR 16.6', title: 'DOJ FOIA responses to requests' },
    ].filter((c) => !q || c.id.toLowerCase().includes(q) || c.title.toLowerCase().includes(q));
  }
}
