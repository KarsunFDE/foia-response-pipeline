import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PERSONA_SWITCHER_PROFILES } from '../models/roles';
import { Role } from '../models/roles';
import { RoleService } from '../services/role.service';

/**
 * Instructor-driven mock role switcher.
 *
 * Production resolves role from JWT in API gateway — this is a
 * local-only override for demo / training purposes. See
 * `RoleService` doc-comment.
 */
@Component({
  selector: 'app-role-switcher',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="role-switcher" [title]="role.current.authorityNote">
      <select [ngModel]="role.currentRole" (ngModelChange)="onSwitch($event)">
        <option *ngFor="let p of profiles" [value]="p.role">
          {{ p.displayName }}
        </option>
      </select>
    </div>
  `,
})
export class RoleSwitcherComponent {
  // FOIA personas + Root + Unauthenticated (acquisition personas excluded — see roles.ts).
  profiles = PERSONA_SWITCHER_PROFILES;

  constructor(public role: RoleService, private router: Router) {}

  onSwitch(next: Role): void {
    this.role.switch(next);
    // Redirect to a role-appropriate landing page so the screen-access
    // pattern is visible to instructor + cohort.
    const landing: Record<Role, string> = {
      // — FOIA roles —
      foia_officer: '/dashboard',
      general_counsel: '/dashboard',
      records_custodian: '/dashboard',
      requester: '/foiaRequests',
      oip_oversight: '/admin/audit',
      // — LEGACY acquisition roles —
      contracting_officer: '/dashboard',
      contract_specialist: '/dashboard',
      program_manager: '/dashboard',
      ssa: '/dashboard',
      evaluator: '/redactionReview/workspace',
      vendor: '/vendor/proposals',
      oig_reviewer: '/admin/findings',
      sys_admin: '/admin/users',
      public: '/public/opportunities',
    };
    this.router.navigateByUrl(landing[next]);
  }
}
