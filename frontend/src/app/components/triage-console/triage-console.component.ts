import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AgentService } from '../../services/agent.service';
import {
  DISPOSITION_OUTCOMES,
  IntakeTriageRequest,
  TriageCitation,
  TriageResult,
} from '../../models/triage';

/**
 * Agentic FOIA triage console (ADR 0005) — the HITL surface.
 *
 * Drives the LangGraph pipeline (intake → classify → route → retrieve →
 * score → analyze → Gate 1 → retrieve precedent → Gate 2 → recommend →
 * Gate 3) through the ai-orchestrator. The system never auto-releases or
 * auto-withholds: a human disposes at each gate (REQ-AGT-2). A side panel
 * runs grounded precedent search (RAG) with low-confidence escalation.
 *
 * Reached from the intake wizard's submit, which hands the intake payload
 * via router state. Calls go through the gateway (AgentService).
 */
@Component({
  selector: 'app-triage-console',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page-header">
      <div>
        <h2>Agentic triage — {{ requestId }}</h2>
        <div class="subtitle">
          ADR 0005 · human-in-the-loop · the system assists, a reviewer decides
          <span class="badge" [ngClass]="statusClass()">{{ statusLabel() }}</span>
        </div>
      </div>
      <div>
        <a [routerLink]="['/foiaRequests', requestId, 'edit']"><button class="secondary">Open request workspace</button></a>
      </div>
    </div>

    <div *ngIf="offlineMode" class="banner offline">
      ⚙ Offline mode — AWS Bedrock credentials not resolved, so the AI nodes use
      a deterministic stub. Retrieval, citations, gates, and escalation are real;
      proposed-exemption text is representative and grounded in the retrieved
      authority. Configure AWS creds for live Claude reasoning.
    </div>
    <div *ngIf="error" class="error-text">{{ error }}</div>
    <div *ngIf="loading" class="card">Running the triage pipeline…</div>

    <div *ngIf="!loading && !startedFromWizard && !result" class="card">
      <p>No intake payload — start a request from the
        <a routerLink="/foiaRequests/new">intake wizard</a>.</p>
    </div>

    <div class="two-col" *ngIf="result">
      <!-- LEFT: pipeline + active gate -->
      <div>
        <div class="card">
          <h3>Pipeline</h3>
          <ol class="pipeline">
            <li *ngFor="let s of stages; let i = index"
                [class.done]="i < activeStage()"
                [class.active]="i === activeStage()">
              {{ s }}
            </li>
          </ol>
        </div>

        <!-- GATE 1 — proposed exemptions -->
        <div class="card" *ngIf="gate() === 'gate-1-proposed-exemptions'">
          <h3>① Review proposed exemptions</h3>
          <p class="muted">{{ pkg()?.summary }}</p>

          <div *ngIf="needsReview()" class="banner review">
            ⚠ {{ reviewReason() || 'Flagged for mandatory human review.' }}
          </div>

          <h4>Proposed exemptions ({{ (pkg()?.proposed_exemptions || []).length }})</h4>
          <div *ngIf="(pkg()?.proposed_exemptions || []).length === 0" class="muted">
            No exemptions proposed at this confidence — reviewer may withhold or release on the record.
          </div>
          <div class="exemption" *ngFor="let ex of pkg()?.proposed_exemptions || []">
            <span class="badge code">{{ ex.exemption_code }}</span>
            <span class="conf" *ngIf="ex.confidence">confidence: {{ ex.confidence }}</span>
            <div>{{ ex.rationale }}</div>
          </div>

          <h4>Cited authority ({{ (pkg()?.citations || []).length }})</h4>
          <ul class="citations">
            <li *ngFor="let c of pkg()?.citations || []">
              <strong>{{ c.cite || c.clause_id }}</strong> — {{ c.title }}
              <span class="muted"> · {{ c.source_file }} · score {{ (c.score || 0) | number:'1.0-2' }}</span>
              <div class="snippet" *ngIf="c.text_snippet">{{ c.text_snippet }}</div>
            </li>
          </ul>

          <div class="gate-actions">
            <button (click)="resume('approved')" [disabled]="busy">Approve exemptions & continue →</button>
            <button class="secondary" (click)="resume('escalated')" [disabled]="busy">Escalate</button>
          </div>
        </div>

        <!-- GATE 2 — precedent scope -->
        <div class="card" *ngIf="gate() === 'gate-2-precedent-scope'">
          <h3>② Review precedent scope</h3>
          <p class="muted">{{ pkg()?.summary }}</p>

          <p><strong>Scoping keywords:</strong>
            <span class="kw" *ngFor="let k of pkg()?.keywords || []">{{ k }}</span>
          </p>

          <h4>Retrieved precedent ({{ (pkg()?.precedent || []).length }})</h4>
          <div *ngIf="(pkg()?.precedent || []).length === 0" class="muted">No precedent returned.</div>
          <ul class="citations">
            <li *ngFor="let p of pkg()?.precedent || []">
              <strong>{{ p.decision_id }}</strong>
              <div class="snippet">{{ p.summary }}</div>
            </li>
          </ul>

          <div class="gate-actions">
            <button (click)="resume('approved')" [disabled]="busy">Approve precedent & continue →</button>
          </div>
          <div class="scope-correct">
            <label><span class="label-text">Correct scope (comma-separated keywords) — re-runs retrieval + analysis</span>
              <input [(ngModel)]="correctedKeywords" placeholder="e.g., deliberative, privacy, surveillance"/>
            </label>
            <button class="secondary" (click)="scopeCorrect()" [disabled]="busy || !correctedKeywords.trim()">
              Scope-correct & loop back
            </button>
          </div>
        </div>

        <!-- GATE 3 — final disposition -->
        <div class="card" *ngIf="gate() === 'gate-3-final-disposition'">
          <h3>③ Final disposition (RISKY — requester-facing)</h3>
          <p class="muted">{{ pkg()?.summary }}</p>

          <div *ngIf="needsReview()" class="banner review">
            ⚠ {{ reviewReason() || 'Under-grounded — escalate unless you can dispose on the record.' }}
          </div>

          <div *ngIf="pkg()?.recommendation as rec" class="rec">
            <p><strong>Recommended outcome:</strong> {{ outcomeLabel(rec.outcome) }}
              <span class="conf" *ngIf="rec.confidence">confidence: {{ rec.confidence }}</span></p>
            <p class="snippet">{{ rec.rationale }}</p>
            <p *ngIf="rec.segregability_analysis"><strong>Segregability:</strong> {{ rec.segregability_analysis }}</p>
          </div>

          <div class="gate-actions">
            <label><span class="label-text">Your disposition</span>
              <select [(ngModel)]="finalOutcome">
                <option *ngFor="let o of outcomes" [value]="o.value">{{ o.label }}</option>
              </select>
            </label>
            <button (click)="finalize()" [disabled]="busy">Sign disposition</button>
            <button class="secondary" (click)="resume('escalated')" [disabled]="busy">Escalate</button>
          </div>
        </div>

        <!-- TERMINAL -->
        <div class="card" *ngIf="result?.status === 'complete'">
          <h3>✓ Disposition recorded</h3>
          <p><strong>Final outcome:</strong> {{ outcomeLabel(result?.final_outcome || '') }}</p>
        </div>
        <div class="card" *ngIf="result?.status === 'escalated'">
          <h3>⚠ Escalated</h3>
          <p>The run was escalated rather than auto-disposed. {{ reviewReason() }}</p>
        </div>

        <!-- AUDIT (on terminal) -->
        <div class="card" *ngIf="(result?.audit_log || []).length > 0">
          <h3>Audit trail</h3>
          <table>
            <thead><tr><th>Stage</th><th>Action</th><th>Detail</th><th>Sources</th></tr></thead>
            <tbody>
              <tr *ngFor="let a of result?.audit_log || []">
                <td>{{ a.stage }}</td>
                <td>{{ a.action }}</td>
                <td class="muted">{{ a.detail }}</td>
                <td class="muted">{{ a.sources.join(', ') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- RIGHT: grounded precedent search -->
      <div>
        <div class="card">
          <h3>FOIA precedent search (RAG)</h3>
          <p class="muted">Hybrid lexical + Atlas over 5 USC 552 / 28 CFR 16. Below-confidence
            results are withheld and escalated.</p>
          <input [(ngModel)]="precedentQuery" (keyup.enter)="searchPrecedent()"
                 placeholder="e.g., deliberative process (b)(5)"/>
          <button (click)="searchPrecedent()" [disabled]="searching" style="margin-top:0.5rem">
            {{ searching ? 'Searching…' : 'Search' }}
          </button>
          <div *ngIf="precedentReview" class="banner review">⚠ {{ precedentReview }}</div>
          <ul class="citations" *ngIf="precedentResults.length > 0">
            <li *ngFor="let c of precedentResults">
              <strong>{{ c.cite || c.clause_id }}</strong> — {{ c.title }}
              <span class="muted"> · score {{ (c.score || 0) | number:'1.0-2' }}</span>
              <div class="snippet" *ngIf="c.text_snippet">{{ c.text_snippet }}</div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .pipeline { list-style:none; padding:0; margin:0; }
    .pipeline li { padding:0.3rem 0.5rem; border-left:3px solid var(--color-border, #ddd); color:var(--color-fg-muted); font-size:0.85rem; }
    .pipeline li.done { border-left-color:#5a8; color:var(--color-fg, #333); }
    .pipeline li.active { border-left-color:var(--color-accent, #d70); font-weight:700; color:var(--color-fg, #111); }
    .muted { color:var(--color-fg-muted); font-size:0.85rem; }
    .banner { padding:0.5rem 0.75rem; border-radius:6px; margin:0.5rem 0; font-size:0.85rem; }
    .banner.review { background:#fde8d3; color:var(--color-accent-dark, #a40); }
    .banner.offline { background:#eef; color:#446; }
    .exemption { border:1px solid var(--color-border,#eee); border-radius:6px; padding:0.4rem 0.6rem; margin-bottom:0.4rem; }
    .badge.code { background:#334; color:#fff; padding:0.05rem 0.4rem; border-radius:4px; font-weight:700; }
    .conf { font-size:0.72rem; color:var(--color-fg-muted); margin-left:0.5rem; }
    .citations { list-style:none; padding:0; }
    .citations li { padding:0.35rem 0; border-bottom:1px solid var(--color-border,#f0f0f0); font-size:0.85rem; }
    .snippet { font-size:0.8rem; color:var(--color-fg-muted); margin-top:0.2rem; white-space:pre-wrap; }
    .kw { background:#eef; border-radius:999px; padding:0.05rem 0.5rem; margin-right:0.3rem; font-size:0.75rem; }
    .gate-actions { margin-top:0.75rem; display:flex; gap:0.5rem; align-items:flex-end; flex-wrap:wrap; }
    .scope-correct { margin-top:0.75rem; padding-top:0.5rem; border-top:1px dashed var(--color-border,#eee); }
  `],
})
export class TriageConsoleComponent implements OnInit {
  requestId = '';
  result: TriageResult | null = null;
  loading = false;
  busy = false;
  error: string | null = null;
  startedFromWizard = false;
  offlineMode = false;

  correctedKeywords = '';
  finalOutcome = 'partial-release-with-redactions';
  outcomes = DISPOSITION_OUTCOMES;

  precedentQuery = '';
  precedentResults: TriageCitation[] = [];
  precedentReview: string | null = null;
  searching = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private agent: AgentService,
  ) {}

  ngOnInit(): void {
    this.requestId = this.route.snapshot.params['id'];
    const intake: IntakeTriageRequest | undefined = history.state?.intake;
    if (intake) {
      this.startedFromWizard = true;
      this.loading = true;
      this.agent.startTriage(intake).subscribe({
        next: (res) => this.apply(res),
        error: (err) => this.fail(err),
      });
    }
  }

  private apply(res: TriageResult): void {
    this.result = res;
    this.loading = false;
    this.busy = false;
    this.detectOffline(res);
  }

  private fail(err: any): void {
    this.error = `Triage call failed: ${err?.message ?? err}`;
    this.loading = false;
    this.busy = false;
  }

  /** The offline stub marks AI prose with "[offline-stub]"; surface that honestly. */
  private detectOffline(res: TriageResult): void {
    const rec = res.recommendation || res.review_package?.recommendation;
    const blob = JSON.stringify(rec || res.review_package || {});
    if (blob.includes('[offline-stub]')) this.offlineMode = true;
  }

  gate(): string | null { return this.result?.gate ?? null; }
  pkg() { return this.result?.review_package ?? null; }
  needsReview(): boolean { return !!(this.pkg()?.needs_review ?? this.result?.needs_review); }
  reviewReason(): string | null { return this.pkg()?.review_reason ?? this.result?.review_reason ?? null; }

  statusLabel(): string {
    switch (this.result?.status) {
      case 'awaiting_review': return 'awaiting review';
      case 'complete': return 'complete';
      case 'escalated': return 'escalated';
      default: return this.result?.status || '';
    }
  }
  statusClass(): string { return (this.result?.status || '').replace('_', '-'); }

  outcomeLabel(v: string): string {
    return this.outcomes.find((o) => o.value === v)?.label ?? v;
  }

  stages = [
    'Intake', 'Classify', 'Route', 'Retrieve authority', 'Score / filter', 'Analyze',
    'Gate 1: Exemptions', 'Retrieve precedent', 'Gate 2: Precedent scope', 'Recommend',
    'Gate 3: Disposition',
  ];

  activeStage(): number {
    switch (this.gate()) {
      case 'gate-1-proposed-exemptions': return 6;
      case 'gate-2-precedent-scope': return 8;
      case 'gate-3-final-disposition': return 10;
      default: return this.stages.length; // terminal — all done
    }
  }

  resume(action: 'approved' | 'escalated' | 'rejected'): void {
    if (!this.result) return;
    this.busy = true;
    this.agent.resumeTriage({ request_id: this.requestId, action }).subscribe({
      next: (res) => this.apply(res),
      error: (err) => this.fail(err),
    });
  }

  scopeCorrect(): void {
    const kws = this.correctedKeywords.split(',').map((k) => k.trim()).filter(Boolean);
    if (!kws.length) return;
    this.busy = true;
    this.agent.resumeTriage({
      request_id: this.requestId, action: 'scope-corrected', corrected_keywords: kws,
    }).subscribe({
      next: (res) => { this.correctedKeywords = ''; this.apply(res); },
      error: (err) => this.fail(err),
    });
  }

  finalize(): void {
    this.busy = true;
    this.agent.resumeTriage({
      request_id: this.requestId, action: 'approved', final_outcome: this.finalOutcome,
    }).subscribe({
      next: (res) => this.apply(res),
      error: (err) => this.fail(err),
    });
  }

  searchPrecedent(): void {
    const q = this.precedentQuery.trim();
    if (!q) return;
    this.searching = true;
    this.precedentReview = null;
    this.agent.clauseSearch(q, { top_k: 5 }).subscribe({
      next: (res) => {
        this.precedentResults = res.hits || [];
        this.precedentReview = res.needs_review
          ? (res.review_reason || 'Flagged for mandatory human review.')
          : null;
        this.searching = false;
      },
      error: (err) => {
        this.precedentReview = `Search failed: ${err?.message ?? err}`;
        this.precedentResults = [];
        this.searching = false;
      },
    });
  }
}
