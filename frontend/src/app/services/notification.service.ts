import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Notification } from '../models/notification';

/**
 * In-app notification bus (bell icon + drawer).
 *
 * Per feature-inventory-target.md notification table. Item 6
 * (correlation-ID mismatch) is reinforced by the fact that this
 * client-side mock generates its own UUID independent of the
 * triggering service-side correlation ID.
 */
@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly subject = new BehaviorSubject<Notification[]>(this.seed());
  readonly items$: Observable<Notification[]> = this.subject.asObservable();

  markRead(id: string): void {
    this.subject.next(
      this.subject.value.map((n) =>
        n.id === id ? { ...n, readAt: new Date().toISOString() } : n,
      ),
    );
  }

  markAllRead(): void {
    const ts = new Date().toISOString();
    this.subject.next(
      this.subject.value.map((n) => ({ ...n, readAt: n.readAt ?? ts })),
    );
  }

  unreadCount(): number {
    return this.subject.value.filter((n) => !n.readAt).length;
  }

  private seed(): Notification[] {
    return [
      {
        id: 'n-1001',
        kind: 'REQUEST_RECEIVED',
        title: 'New FOIA request received — DOJ-2026-002847',
        body: 'Journalist requester seeks "all emails between OLP staff and outside counsel re: surveillance guidance, Jan–Mar 2026." Logged under 5 USC 552(a)(3)(A).',
        recipientRole: 'foia_officer',
        link: '/foiaRequests/DOJ-2026-002847/edit',
        createdAt: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
        readAt: null,
      },
      {
        id: 'n-1002',
        kind: 'CLOCK_DUE_SOON',
        title: '20-working-day clock — response due in 3 days (DOJ-2026-002791)',
        body: 'Statutory determination due 2026-06-02 under 5 USC 552(a)(6)(A)(i). No unusual-circumstances extension tolled.',
        recipientRole: 'foia_officer',
        link: '/foiaRequests/DOJ-2026-002791/edit',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
        readAt: null,
      },
      {
        id: 'n-1003',
        kind: 'EXEMPTION_REVIEW_READY',
        title: 'Exemption analysis ready for review — DOJ-2026-002791',
        body: 'Records custodian proposes (b)(5) deliberative-process and (b)(7)(C) personal-privacy withholdings on 14 of 38 pages. General Counsel sign-off required (5 USC 552(b)).',
        recipientRole: 'general_counsel',
        link: '/redactionReview/workspace',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 8).toISOString(),
        readAt: null,
      },
      {
        id: 'n-1004',
        kind: 'REDACTION_HITL_PENDING',
        title: 'Redaction review needs HITL approval before release — DOJ-2026-002715',
        body: 'AI-proposed redactions staged; human reviewer must approve before any production. Auto-release is blocked pending sign-off.',
        recipientRole: 'general_counsel',
        link: '/redactionReview/DOJ-2026-002715/consensus',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 11).toISOString(),
        readAt: null,
      },
      {
        id: 'n-1005',
        kind: 'RESPONSE_SENT',
        title: 'Response sent (partial grant) — DOJ-2026-002680',
        body: '212 pages released, 9 withheld in full under (b)(1). Requester notified of appeal rights per 5 USC 552(a)(6)(A)(i).',
        recipientRole: 'foia_officer',
        link: '/foiaRequests/DOJ-2026-002680/edit',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 20).toISOString(),
        readAt: null,
      },
      {
        id: 'n-1006',
        kind: 'APPEAL_FILED',
        title: 'Administrative appeal filed — DOJ-2026-002603-A1',
        body: 'Requester appeals adequacy-of-search and (b)(5) withholdings (5 USC 552(a)(6)(A)(ii)). 20-working-day appeal clock started.',
        recipientRole: 'general_counsel',
        link: '/foiaRequests/DOJ-2026-002603/edit',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
        readAt: null,
      },
      {
        id: 'n-1007',
        kind: 'OIP_OVERSIGHT_ITEM',
        title: 'OIP oversight item — annual FOIA compliance pull',
        body: 'OIP requests backlog + median-response-time metrics for the FOIA-Improvement-Act self-assessment. Read-only export queued.',
        recipientRole: 'oip_oversight',
        link: '/admin/audit',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
        readAt: new Date(Date.now() - 1000 * 60 * 60 * 47).toISOString(),
      },
    ];
  }
}
