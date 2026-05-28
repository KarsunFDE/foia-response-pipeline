import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { FoiaRequestService } from '../../services/foia-request.service';
import {
  FoiaRequest,
  FoiaRequestCreate,
  RequesterType,
  FeeCategory,
} from '../../models/foia-request';

/**
 * Multi-step FOIA Request Intake Wizard (5 USC 552(a)).
 *
 * Steps mirror the FOIA intake flow, not an RFP build:
 *   Step 1: Requester (name, org, type) — type derives the fee category
 *   Step 2: Records sought (description, date range)
 *   Step 3: Fee category (derived) + fee-waiver toggle
 *   Step 4: Expedited-processing request + justification
 *   Step 5: Review + submit to INTAKE_TRIAGE (starts the 20-working-day clock)
 *
 * AI-assist (POST /draft-foia-request) drafts the acknowledgement / response
 * letter — replacing the old Section-C SOW drafter.
 *
 * Touches Item 4 (no Pydantic schema on AI output), Item 5 (legacy
 * LLMChain wired into the AI-orchestrator drafter), Item 9 (no
 * sanitization on the records-sought free-text field — feeds the prompt).
 */
@Component({
  selector: 'app-foiaRequest-wizard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-header">
      <div>
        <h2>New FOIA request — intake wizard</h2>
        <div class="subtitle">5 USC 552(a) · 20-working-day clock starts on submit · AI-assisted</div>
      </div>
    </div>

    <div class="stepper">
      <span class="step" *ngFor="let s of steps; let i = index"
            [class.active]="i === step"
            [class.complete]="i < step">{{ i + 1 }}. {{ s }}</span>
    </div>

    <!-- Step 1: Requester -->
    <div class="card" *ngIf="step === 0">
      <h3>1. Requester</h3>
      <p style="font-size:0.85rem;color:var(--color-fg-muted)">
        ⚠ The requester is an external, potentially adversarial party
        (inverted threat model). Treat all fields as untrusted input.
      </p>
      <div class="two-col">
        <label><span class="label-text">Requester name</span>
          <input name="requesterName" [(ngModel)]="model.requesterName" placeholder="e.g., J. Alvarez"/>
        </label>
        <label><span class="label-text">Organization (if any)</span>
          <input name="requesterOrg" [(ngModel)]="model.requesterOrg" placeholder="e.g., The Sunlight Beacon"/>
        </label>
      </div>
      <label><span class="label-text">Requester type (sets fee category — 5 USC 552(a)(4)(A))</span>
        <select name="requesterType" [(ngModel)]="model.requesterType" (ngModelChange)="onRequesterType()">
          <option value="commercial">Commercial use</option>
          <option value="news_media_educational_scientific">News media / educational / scientific</option>
          <option value="other">Other (incl. individuals)</option>
        </select>
      </label>
    </div>

    <!-- Step 2: Records sought -->
    <div class="card" *ngIf="step === 1">
      <h3>2. Records sought</h3>
      <label><span class="label-text">Short subject line</span>
        <input name="title" [(ngModel)]="model.title" placeholder="e.g., Deliberative memos on FOIA backlog policy"/>
      </label>
      <label><span class="label-text">Description of records sought</span>
        <textarea name="recordsSought" rows="6" [(ngModel)]="model.recordsSought"
                  placeholder="Describe the records as specifically as possible (rendered raw — see Debt Item 9)"></textarea>
      </label>
      <div class="two-col">
        <label><span class="label-text">Date range — start</span>
          <input name="dateRangeStart" type="date" [(ngModel)]="model.dateRangeStart"/>
        </label>
        <label><span class="label-text">Date range — end</span>
          <input name="dateRangeEnd" type="date" [(ngModel)]="model.dateRangeEnd"/>
        </label>
      </div>
      <button class="secondary" (click)="aiDraft('acknowledgement')">▦ AI-draft acknowledgement letter</button>
      <p style="font-size:0.8rem;color:var(--color-fg-muted)">
        AI-drafted via <code>POST /draft-foia-request</code>.
        ⚠ Debt Item 4 (no Pydantic schema), Item 5 (legacy LLMChain wired here).
      </p>
      <textarea *ngIf="draftLetter" name="draftLetter" rows="6" [(ngModel)]="draftLetter" style="margin-top:0.5rem"></textarea>
    </div>

    <!-- Step 3: Fee -->
    <div class="card" *ngIf="step === 2">
      <h3>3. Fees</h3>
      <p style="font-size:0.85rem;color:var(--color-fg-muted)">
        Fee category is derived from requester type (5 USC 552(a)(4)(A)(ii)).
      </p>
      <table>
        <tbody>
          <tr><th>Requester type</th><td>{{ model.requesterType }}</td></tr>
          <tr><th>Derived fee category</th><td><strong>{{ model.feeCategory }}</strong></td></tr>
          <tr><th>Chargeable</th><td>{{ feeNarrative() }}</td></tr>
        </tbody>
      </table>
      <label style="margin-top:0.75rem">
        <input type="checkbox" name="feeWaiver" [(ngModel)]="model.feeWaiverRequested" style="width:auto"/>
        Requester is asking for a fee waiver (public-interest test)
      </label>
    </div>

    <!-- Step 4: Expedited processing -->
    <div class="card" *ngIf="step === 3">
      <h3>4. Expedited processing (5 USC 552(a)(6)(E))</h3>
      <label>
        <input type="checkbox" name="expedited" [(ngModel)]="model.expeditedProcessingRequested" style="width:auto"/>
        Requester is asking for expedited processing
      </label>
      <label *ngIf="model.expeditedProcessingRequested"><span class="label-text">Justification (compelling need)</span>
        <textarea name="expeditedJustification" rows="4" [(ngModel)]="model.expeditedJustification"
                  placeholder="e.g., imminent threat to life/safety, or urgency to inform the public on a matter of current interest"></textarea>
      </label>
    </div>

    <!-- Step 5: Review -->
    <div class="card" *ngIf="step === 4">
      <h3>5. Review &amp; submit to intake triage</h3>
      <p>Submitting transitions the request to <code>INTAKE_TRIAGE</code> and
         <strong>starts the 20-working-day statutory clock</strong> (5 USC 552(a)(6)(A)).</p>
      <table>
        <tbody>
          <tr><th>Requester</th><td>{{ model.requesterName || '—' }} ({{ model.requesterOrg || 'individual' }})</td></tr>
          <tr><th>Type / fee category</th><td>{{ model.requesterType }} / {{ model.feeCategory }}</td></tr>
          <tr><th>Subject</th><td>{{ model.title || '—' }}</td></tr>
          <tr><th>Records sought</th><td>{{ (model.recordsSought || '').length }} chars</td></tr>
          <tr><th>Date range</th><td>{{ model.dateRangeStart || '—' }} → {{ model.dateRangeEnd || '—' }}</td></tr>
          <tr><th>Fee waiver requested</th><td>{{ model.feeWaiverRequested ? 'Yes' : 'No' }}</td></tr>
          <tr><th>Expedited requested</th><td>{{ model.expeditedProcessingRequested ? 'Yes' : 'No' }}</td></tr>
        </tbody>
      </table>
    </div>

    <div style="margin-top:1rem;display:flex;gap:0.5rem;justify-content:space-between">
      <button class="secondary" (click)="back()" [disabled]="step === 0">← Back</button>
      <div>
        <button *ngIf="step < steps.length - 1" (click)="next()">Next →</button>
        <button *ngIf="step === steps.length - 1" (click)="submit()" [disabled]="submitting">
          {{ submitting ? 'Submitting…' : 'Submit to intake triage' }}
        </button>
      </div>
    </div>
    <div *ngIf="error" class="error-text">{{ error }}</div>
  `,
})
export class FoiaRequestWizardComponent {
  steps = ['Requester', 'Records sought', 'Fees', 'Expedited', 'Review'];
  step = 0;
  submitting = false;
  error: string | null = null;
  draftLetter = '';

  model: FoiaRequestCreate = {
    agencyId: 'DOJ-OIP',
    title: '',
    recordsSought: '',
    status: 'INTAKE_TRIAGE',
    requesterName: '',
    requesterOrg: '',
    requesterType: 'other',
    feeCategory: 'other',
    feeWaiverRequested: false,
    expeditedProcessingRequested: false,
  };

  constructor(private svc: FoiaRequestService, private router: Router) {}

  back(): void {
    if (this.step > 0) this.step--;
  }

  next(): void {
    if (this.step < this.steps.length - 1) this.step++;
  }

  /** Fee category is derived from requester type (5 USC 552(a)(4)(A)(ii)). */
  onRequesterType(): void {
    this.model.feeCategory = (this.model.requesterType ?? 'other') as FeeCategory;
  }

  feeNarrative(): string {
    switch (this.model.requesterType as RequesterType) {
      case 'commercial':
        return 'Search + review + duplication.';
      case 'news_media_educational_scientific':
        return 'Duplication only, after the first 100 pages free.';
      default:
        return 'Search after the first 2 hours free + duplication after 100 pages free.';
    }
  }

  aiDraft(kind: 'acknowledgement'): void {
    // Stubbed — in W2 this hits POST /draft-foia-request through the
    // gateway. For instructor demo, populate plausible placeholder text.
    this.draftLetter =
      `Dear ${this.model.requesterName || 'Requester'},\n\n` +
      `This acknowledges receipt of your Freedom of Information Act request ` +
      `regarding "${this.model.title || '[subject]'}". Your request has been ` +
      `assigned a tracking number and entered intake triage. Under 5 USC ` +
      `552(a)(6)(A), the agency will respond within 20 working days; we will ` +
      `notify you if unusual circumstances require up to 10 additional working ` +
      `days.\n\nRecords sought: ${this.model.recordsSought || '[description not yet entered]'}\n\n` +
      `[AI-DRAFTED placeholder — FOIA Officer reviews before sending. ` +
      `Item 4 / Item 5 surface.]`;
  }

  submit(): void {
    this.submitting = true;
    this.error = null;
    const payload: FoiaRequestCreate = {
      ...this.model,
      status: 'INTAKE_TRIAGE',
      receivedDate: new Date().toISOString(),
    };
    this.svc.create(payload).subscribe({
      next: (s: FoiaRequest) => {
        this.submitting = false;
        this.router.navigate(['/foiaRequests', s.id || 'foia-new', 'edit']);
      },
      error: () => {
        // Brownfield reality: create may fail; for instructor demo, still
        // route to the list as if it succeeded.
        this.submitting = false;
        this.router.navigate(['/foiaRequests']);
      },
    });
  }
}
