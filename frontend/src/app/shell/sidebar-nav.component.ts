import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { Subscription } from 'rxjs';
import { RoleService } from '../services/role.service';
import { Role, RoleProfile } from '../models/roles';

interface NavLink {
  label: string;
  route: string;
  roles: Role[];           // empty = visible to all authenticated
}
interface NavGroup {
  title: string;
  links: NavLink[];
}

const ALL_AUTHENTICATED: Role[] = [
  'foia_officer', 'general_counsel', 'records_custodian', 'oip_oversight',
  'contracting_officer', 'contract_specialist', 'program_manager',
  'ssa', 'evaluator', 'vendor', 'oig_reviewer', 'sys_admin',
];

const FOIA_STAFF: Role[] = ['foia_officer', 'general_counsel', 'records_custodian'];

// FOIA workflow: INTAKE_TRIAGE → EXEMPTION_ANALYSIS → REDACTION_PROPOSAL →
// HITL_REVIEW → RESPONSE → APPEAL (domain-mapping.md). Links stay on the
// existing app.routes.ts paths — no route paths were added or changed. Stages
// without a dedicated route (Responses / Appeals) point at the relevant
// /foiaRequests/:id/edit record so the workflow is navigable today; the pair
// adds purpose-built routes in W4–W5.
const NAV: NavGroup[] = [
  {
    title: 'Requests',
    links: [
      { label: 'Officer Dashboard', route: '/dashboard', roles: [...FOIA_STAFF, 'oip_oversight'] },
      { label: 'Request Index', route: '/foiaRequests', roles: [...FOIA_STAFF, 'oip_oversight', 'requester'] },
      { label: 'New Request', route: '/foiaRequests/new', roles: FOIA_STAFF },
    ],
  },
  {
    title: 'Exemption Analysis',
    links: [
      { label: 'Exemption Queue', route: '/redactionReviews', roles: ['foia_officer', 'general_counsel', 'records_custodian'] },
    ],
  },
  {
    title: 'Redaction Review',
    links: [
      { label: 'Consensus Review', route: '/redactionReview/rr-0142/consensus', roles: ['foia_officer', 'general_counsel'] },
    ],
  },
  {
    title: 'Responses',
    links: [
      // RESPONSE-stage record (release determination) — existing /foiaRequests/:id/edit route.
      { label: 'Release Responses', route: '/foiaRequests/foia-2026-0203/edit', roles: ['foia_officer', 'general_counsel'] },
    ],
  },
  {
    title: 'Appeals',
    links: [
      // APPEAL-stage record — existing /foiaRequests/:id/edit route.
      { label: 'Appeals Queue', route: '/foiaRequests/foia-2026-0418/edit', roles: ['foia_officer', 'general_counsel', 'oip_oversight'] },
    ],
  },
  {
    title: 'Reports',
    links: [
      { label: 'FOIA Reports', route: '/reports', roles: [...FOIA_STAFF, 'oip_oversight', 'sys_admin', 'oig_reviewer'] },
      { label: 'Audit Log', route: '/admin/audit', roles: [...FOIA_STAFF, 'oip_oversight', 'sys_admin', 'oig_reviewer'] },
    ],
  },
  {
    title: 'Admin',
    links: [
      { label: 'User & Role Admin', route: '/admin/users', roles: ['sys_admin'] },
      { label: 'System Config', route: '/admin/config', roles: ['sys_admin'] },
      { label: 'OIG Findings Tracker', route: '/admin/findings', roles: ['sys_admin', 'oig_reviewer'] },
    ],
  },
  // — Legacy (pre-FOIA) acquisition nav — orphaned sections with no FOIA
  // mapping yet. Retained, not deleted; the pair repurposes/removes in W4–W5.
  {
    title: 'Legacy (pre-FOIA)',
    links: [
      { label: 'Public Opportunity Search', route: '/public/opportunities', roles: [] },
      { label: 'Evaluator Workspace', route: '/redactionReview/workspace', roles: ['evaluator', 'contracting_officer'] },
      { label: 'Vendor Portal', route: '/vendor/proposals', roles: ['vendor'] },
      { label: 'Vendor Directory', route: '/vendors', roles: ['contracting_officer', 'contract_specialist', 'evaluator', 'program_manager'] },
      { label: 'Award Record', route: '/awards/aw-2026-001', roles: ['contracting_officer', 'program_manager', 'vendor'] },
      { label: 'Contract Admin', route: '/contracts/ctr-0001/admin', roles: ['contracting_officer', 'program_manager'] },
      { label: 'CPAR Reviews', route: '/contracts/ctr-0001/cpars', roles: ['contracting_officer', 'program_manager', 'vendor'] },
    ],
  },
];

@Component({
  selector: 'app-sidebar-nav',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  template: `
    <nav class="sidebar">
      <ng-container *ngFor="let group of visibleGroups; trackBy: trackGroup">
        <div class="sidebar-section-title">{{ group.title }}</div>
        <a *ngFor="let link of group.links; trackBy: trackLink"
           [routerLink]="link.route"
           routerLinkActive="active">{{ link.label }}</a>
      </ng-container>
    </nav>
  `,
})
export class SidebarNavComponent implements OnInit, OnDestroy {
  visibleGroups: NavGroup[] = [];
  private sub?: Subscription;

  constructor(public role: RoleService) {}

  ngOnInit(): void {
    this.recompute(this.role.currentRole);
    this.sub = this.role.profile$.subscribe((p) => this.recompute(p.role));
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  trackGroup = (_: number, g: NavGroup) => g.title;
  trackLink = (_: number, l: NavLink) => l.route;

  private recompute(current: Role): void {
    this.visibleGroups = NAV
      .map((g) => ({
        ...g,
        links: g.links.filter((l) =>
          l.roles.length === 0 || l.roles.includes(current) || current === 'sys_admin',
        ),
      }))
      .filter((g) => g.links.length > 0);
  }
}
