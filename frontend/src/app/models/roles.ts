/**
 * FOIA-processing role model (5 USC 552, 28 CFR 16).
 *
 * Mirrors the JWT `role` claim. FedRAMP RBAC AC-2/AC-5 (least-privilege +
 * separation-of-duties). The FOIA threat model is INVERTED — the
 * `requester` is an external, potentially adversarial party, so requester
 * authority is read-only and externally scoped.
 *
 * NOTE: this is a mock role-switcher for cohort instructor demos.
 * Production RBAC resolves role from validated JWT in the API gateway
 * (which today has Debt Item 1 — JWT signature-skip on `/api/public/*`).
 *
 * The acquisition-era roles below the FOIA set (contracting_officer, vendor,
 * etc.) are LEGACY — retained only so the inherited acquisition components +
 * route guards still compile. The pair repurposes/removes them in W4–W5.
 */
export type Role =
  // — FOIA roles —
  | 'foia_officer'
  | 'general_counsel'
  | 'records_custodian'
  | 'requester'
  | 'oip_oversight'
  // — LEGACY acquisition roles (inherited; repurposed/removed W4–W5) —
  | 'contracting_officer'
  | 'contract_specialist'
  | 'program_manager'
  | 'ssa'
  | 'evaluator'
  | 'vendor'
  | 'oig_reviewer'
  | 'sys_admin'
  | 'public';

export interface RoleProfile {
  role: Role;
  displayName: string;
  agencyId: string | null;   // null for cross-tenant (sys_admin/oip) + external (requester/public)
  vendorDuns?: string;       // LEGACY — only present for `vendor`
  /** Authority notes shown in role-switcher tooltip (FOIA cites 5 USC 552 / 28 CFR 16). */
  authorityNote: string;
}

export const ROLE_PROFILES: RoleProfile[] = [
  // — FOIA roles —
  {
    role: 'foia_officer',
    displayName: 'Dana Reeves (FOIA Officer, DOJ-OIP)',
    agencyId: 'DOJ-OIP',
    authorityNote: 'Triage requests, set fee category, run the 20-working-day clock (5 USC 552(a)(6)).',
  },
  {
    role: 'general_counsel',
    displayName: 'Col. Whitfield (General Counsel)',
    agencyId: 'DOJ-OIP',
    authorityNote: 'Approve/withhold release; sign exemption determinations (5 USC 552(b)).',
  },
  {
    role: 'records_custodian',
    displayName: 'Priya Shah (Records Custodian)',
    agencyId: 'DOJ-OIP',
    authorityNote: 'Locate + produce responsive records; assert (b)(1)/(b)(7) source restrictions.',
  },
  {
    role: 'requester',
    displayName: 'External Requester (journalist / public)',
    agencyId: null,
    authorityNote: '⚠ EXTERNAL / UNTRUSTED — submit requests, track status, file appeals (5 USC 552(a)(6)(A)(i)). Inverted threat model.',
  },
  {
    role: 'oip_oversight',
    displayName: 'OIP / DOJ Oversight',
    agencyId: null,
    authorityNote: 'Read-only across agencies; FOIA-Improvement-Act compliance reporting.',
  },
  // — LEGACY acquisition roles (inherited; repurposed/removed W4–W5) —
  {
    role: 'contracting_officer',
    displayName: 'Dana Reeves (CO, GSA-FAS)',
    agencyId: 'GSA-FAS',
    authorityNote: 'Sign award, issue amendment, terminate contract (FAR 1.602-1).',
  },
  {
    role: 'contract_specialist',
    displayName: 'Miguel Ortiz (CS, GSA-FAS)',
    agencyId: 'GSA-FAS',
    authorityNote: 'Draft foiaRequests; cannot sign award (FAR 1.603).',
  },
  {
    role: 'program_manager',
    displayName: 'Priya Shah (PM, GSA-FAS)',
    agencyId: 'GSA-FAS',
    authorityNote: 'Requirements + CPAR draft (FAR 42.1503).',
  },
  {
    role: 'ssa',
    displayName: 'Col. Whitfield (SSA, GSA-FAS)',
    agencyId: 'GSA-FAS',
    authorityNote: 'Source Selection Authority — final award (FAR 15.303(b)(6)).',
  },
  {
    role: 'evaluator',
    displayName: 'Dr. Allen (TEP evaluator, GSA-FAS)',
    agencyId: 'GSA-FAS',
    authorityNote: 'Score assigned proposals against Section M (FAR 15.305).',
  },
  {
    role: 'vendor',
    displayName: 'Acme Federal LLC (DUNS 12-345-6789)',
    agencyId: null,
    vendorDuns: '123456789',
    authorityNote: 'Submit proposals; rebuttal on CPAR (FAR 42.1503(d)).',
  },
  {
    role: 'oig_reviewer',
    displayName: 'Inspector Park (OIG)',
    agencyId: 'GSA-OIG',
    authorityNote: 'Read-only across tenants; open findings.',
  },
  {
    role: 'sys_admin',
    displayName: 'Root (sys_admin)',
    agencyId: null,
    authorityNote: 'Cross-tenant admin; provisioning + key rotation.',
  },
  {
    role: 'public',
    displayName: 'Unauthenticated visitor',
    agencyId: null,
    authorityNote: 'Read-only on /public/* (Item 1 surface).',
  },
];

/**
 * Curated persona list for the instructor-demo role switcher.
 *
 * Acquisition personas (CO / CS / PM / SSA / evaluator / vendor / OIG) are
 * EXCLUDED here — they remain in `ROLE_PROFILES` (and the `Role` union) only
 * so the inherited route guards + landing maps still compile until the pair
 * removes them in W4–W5. The switcher itself shows FOIA personas plus the
 * cross-cutting Root + Unauthenticated entries.
 *
 * `requester` is flagged adversarial per the inverted FOIA threat model.
 */
const PERSONA_SWITCHER_ROLES: Role[] = [
  'foia_officer',     // default
  'general_counsel',
  'records_custodian',
  'requester',        // ⚠ external / potentially adversarial
  'oip_oversight',    // OIP / DOJ oversight
  'sys_admin',        // Root
  'public',           // Unauthenticated
];

export const PERSONA_SWITCHER_PROFILES: RoleProfile[] = PERSONA_SWITCHER_ROLES
  .map((r) => ROLE_PROFILES.find((p) => p.role === r)!)
  .filter(Boolean);
