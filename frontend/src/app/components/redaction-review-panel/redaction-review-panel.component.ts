import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-redactionReview-panel',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2>Redaction review</h2>
    <p>
      <em>
        Stub view. The redaction-review UI (exemption proposal → reviewer
        challenge → HITL release/withhold) is part of W3 cohort work —
        multi-agent coordination + HITL interrupt nodes on irreversible release.
      </em>
    </p>
    <button (click)="createPanel()">Create stub redaction review</button>
    <pre *ngIf="result">{{ result | json }}</pre>
    <p *ngIf="error" style="color: crimson">{{ error }}</p>
  `,
})
export class RedactionReviewPanelComponent {
  result: unknown = null;
  error: string | null = null;

  constructor(private http: HttpClient) {}

  createPanel(): void {
    this.error = null;
    this.http
      .post(`${environment.apiGatewayUrl}/api/redaction-reviews`, {
        foiaRequestId: 'stub-foiaRequest-id',
      })
      .subscribe({
        next: (r) => (this.result = r),
        error: (e) => (this.error = `Failed: ${e.message ?? e}`),
      });
  }
}
