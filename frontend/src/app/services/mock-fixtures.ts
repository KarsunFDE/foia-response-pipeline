/**
 * Instructor-demo fixtures.
 *
 * The foia-response-pipeline backend endpoints are scaffold-level; many
 * return empty or 404 against the current legacy stack. To keep
 * instructor-driven demos showing realistic FOIA-processing data even
 * without a fully populated DB, every page falls back to these fixtures on
 * HTTP error.
 *
 * Realism citations (FOIA — retrieved 2026-05-28 via /web-research):
 *   - FOIA.gov tracking-number convention + requester types
 *   - 5 USC 552(a)(6)(A) — 20-working-day response clock
 *   - 5 USC 552(a)(4)(A)(ii) — commercial / news-media-edu-sci / other fee categories
 *   - 5 USC 552(b)(1)–(b)(9) — the nine exemptions
 *
 * NOTE: the `FIXTURE_SOLICITATIONS` / `FIXTURE_EVALUATION` export NAMES are
 * kept (acquisition-era) so the 19 inherited components still import them;
 * the DATA inside is now FOIA. The pair renames the exports in W4–W5.
 */

import { FoiaRequest, FoiaRequestState } from '../models/foia-request';
import { Amendment } from '../models/amendment';
import { Qna } from '../models/qna';
import { Proposal } from '../models/proposal';
import {
  RedactionReview,
  RedactionReviewScore,
  LegacyTepReview,
} from '../models/redaction-review';
import { Award, ContractModification, Deliverable, Cpar } from '../models/award';
import { Vendor } from '../models/vendor';
import { AuditEvent } from '../models/audit';
import { Finding } from '../models/finding';

/** + N working days from now, as an ISO date (approx — ignores holidays). */
function plusWorkingDays(n: number): string {
  const d = new Date();
  let added = 0;
  while (added < n) {
    d.setDate(d.getDate() + 1);
    const day = d.getDay();
    if (day !== 0 && day !== 6) added++;
  }
  return d.toISOString();
}

/** Sample FOIA requests — one per requester type + an at-risk + an appeal. */
export const FIXTURE_SOLICITATIONS: FoiaRequest[] = [
  {
    id: 'foia-2026-0142',
    trackingNumber: 'DOJ-2026-0142',
    agencyId: 'DOJ-OIP',
    title: 'Deliberative memos on FOIA backlog policy',
    recordsSought:
      'All inter- and intra-agency memoranda discussing the 2025 FOIA backlog-reduction policy, including draft guidance circulated for comment.',
    status: 'EXEMPTION_ANALYSIS' as FoiaRequestState,
    requesterName: 'J. Alvarez',
    requesterOrg: 'The Sunlight Beacon (news outlet)',
    requesterType: 'news_media_educational_scientific',
    feeCategory: 'news_media_educational_scientific',
    feeWaiverRequested: true,
    expeditedProcessingRequested: false,
    dateRangeStart: '2025-01-01',
    dateRangeEnd: '2025-12-31',
    receivedDate: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14).toISOString(),
    dueDate: plusWorkingDays(6),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14).toISOString(),
  },
  {
    id: 'foia-2026-0203',
    trackingNumber: 'DOJ-2026-0203',
    agencyId: 'DOJ-OIP',
    title: 'Vendor pricing in cloud-services contract files',
    recordsSought:
      'Unit-pricing tables and proprietary cost narratives submitted by the awardee of contract GS-35F-0001V.',
    status: 'REDACTION_PROPOSAL' as FoiaRequestState,
    requesterName: 'Initech Research LLC',
    requesterOrg: 'Initech Research LLC',
    requesterType: 'commercial',
    feeCategory: 'commercial',
    feeWaiverRequested: false,
    expeditedProcessingRequested: false,
    dateRangeStart: '2023-01-01',
    dateRangeEnd: '2024-06-30',
    receivedDate: new Date(Date.now() - 1000 * 60 * 60 * 24 * 9).toISOString(),
    dueDate: plusWorkingDays(11),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 9).toISOString(),
  },
  {
    id: 'foia-2026-0301',
    trackingNumber: 'DOJ-2026-0301',
    agencyId: 'DOJ-OIP',
    title: 'Records re: agency response to public-records audit',
    recordsSought:
      'Correspondence between the agency CIO and OIP concerning the FY25 records-management audit findings.',
    status: 'INTAKE_TRIAGE' as FoiaRequestState,
    requesterName: 'M. Okafor',
    requesterOrg: 'Private citizen',
    requesterType: 'other',
    feeCategory: 'other',
    feeWaiverRequested: false,
    expeditedProcessingRequested: true,
    expeditedJustification:
      'Pending litigation deadline; records are time-sensitive to an upcoming hearing.',
    receivedDate: new Date(Date.now() - 1000 * 60 * 60 * 24 * 19).toISOString(),
    // ⚠ at statutory risk — due in 1 working day.
    dueDate: plusWorkingDays(1),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 19).toISOString(),
  },
  {
    id: 'foia-2026-0418',
    trackingNumber: 'DOJ-2026-0418',
    agencyId: 'DOJ-OIP',
    title: 'Appeal — partial denial of law-enforcement records',
    recordsSought:
      'Appeal of the partial denial in DOJ-2026-0095; requester challenges the (b)(7)(C) withholdings.',
    status: 'APPEAL' as FoiaRequestState,
    requesterName: 'Civic Transparency Project',
    requesterOrg: 'Civic Transparency Project (watchdog)',
    requesterType: 'news_media_educational_scientific',
    feeCategory: 'news_media_educational_scientific',
    feeWaiverRequested: true,
    expeditedProcessingRequested: false,
    receivedDate: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(),
    dueDate: plusWorkingDays(16),
    disposition: 'partial_grant',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(),
  },
];

/** Sample exemption-driven redaction reviews (the FOIA review shape). */
export const FIXTURE_REDACTION_REVIEWS: RedactionReview[] = [
  {
    id: 'rr-0142',
    foiaRequestId: 'foia-2026-0142',
    agencyId: 'DOJ-OIP',
    documentRef: 'doc-0142-backlog-memo-v3.pdf',
    proposedRedactions: [
      {
        id: 'pr-1',
        segmentRef: 'p.4 ¶2–3',
        exemptions: ['(b)(5)'],
        rationale:
          'Pre-decisional draft recommendation; deliberative-process privilege applies (5 USC 552(b)(5)).',
      },
      {
        id: 'pr-2',
        segmentRef: 'p.7 signature block',
        exemptions: ['(b)(6)'],
        rationale:
          'Personal cell number of a staff attorney; clearly unwarranted privacy invasion (b)(6).',
      },
    ],
    reviewerRole: 'general_counsel',
    state: 'UNDER_REVIEW',
    releaseDecision: null,
    appealable: true,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
    decidedAt: null,
  },
  {
    id: 'rr-0203',
    foiaRequestId: 'foia-2026-0203',
    agencyId: 'DOJ-OIP',
    documentRef: 'doc-0203-pricing-tables.xlsx',
    proposedRedactions: [
      {
        id: 'pr-3',
        segmentRef: 'Tab "Unit Pricing" cols D–H',
        exemptions: ['(b)(4)'],
        rationale:
          'Confidential commercial pricing; substantial competitive harm on release (5 USC 552(b)(4)).',
      },
    ],
    reviewerRole: 'foia_officer',
    state: 'PROPOSED',
    releaseDecision: null,
    appealable: true,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    decidedAt: null,
  },
];

export const FIXTURE_AMENDMENTS: Amendment[] = [
  {
    id: 'am-0001',
    foiaRequestId: 'sol-0142',
    number: 1,
    changeSummary: 'Add CMMC Level 2 attestation to Section H minimum requirements.',
    effectiveAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
    requiresAcknowledgement: true,
    acknowledgedBy: ['vnd-acme', 'vnd-globex'],
    issuedBy: 'co-reeves',
    issuedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
  },
  {
    id: 'am-0002',
    foiaRequestId: 'sol-0142',
    number: 2,
    changeSummary: 'Extend proposal deadline by 7 days; clarify Section L page limit (60 pages including ToC).',
    effectiveAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    requiresAcknowledgement: true,
    acknowledgedBy: ['vnd-acme'],
    issuedBy: 'co-reeves',
    issuedAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
  },
];

export const FIXTURE_QNA: Qna[] = [
  {
    id: 'qa-001',
    foiaRequestId: 'sol-0142',
    question: 'Is the FedRAMP Moderate baseline a hard requirement at proposal submission or by award date?',
    answer: 'FedRAMP Moderate authorization (or In-Process status with completion path documented) is required at proposal submission per Section L.5.2.',
    vendorId: 'vnd-acme',
    postedAt: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 22).toISOString(),
    status: 'PUBLISHED',
  },
  {
    id: 'qa-002',
    foiaRequestId: 'sol-0142',
    question: 'Can past performance from a parent-company contract be cited?',
    answer: null,
    vendorId: 'vnd-globex',
    postedAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
    publishedAt: null,
    status: 'DRAFT_ANSWER',
  },
  {
    id: 'qa-003',
    foiaRequestId: 'sol-0142',
    question: 'What is the period of performance start date assumed for Volume III pricing?',
    answer: null,
    vendorId: 'vnd-initech',
    postedAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    publishedAt: null,
    status: 'NEW',
  },
];

export const FIXTURE_PROPOSALS: Proposal[] = [
  {
    id: 'prop-001',
    foiaRequestId: 'sol-0142',
    vendorId: 'vnd-acme',
    vendorName: 'Acme Federal LLC',
    volumes: [
      { volume: 'I_TECHNICAL', attachmentId: 'att-001', pageCount: 58, submittedAt: new Date().toISOString() },
      { volume: 'II_PAST_PERFORMANCE', attachmentId: 'att-002', pageCount: 22, submittedAt: new Date().toISOString() },
      { volume: 'III_PRICE', attachmentId: 'att-003', pageCount: 12, submittedAt: new Date().toISOString() },
    ],
    submittedAt: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
    sealedUntil: new Date(Date.now() + 1000 * 60 * 60 * 24 * 14).toISOString(),
    amendmentAcks: [1, 2],
  },
  {
    id: 'prop-002',
    foiaRequestId: 'sol-0142',
    vendorId: 'vnd-globex',
    vendorName: 'Globex Federal Systems',
    volumes: [
      { volume: 'I_TECHNICAL', attachmentId: 'att-101', pageCount: 60, submittedAt: new Date().toISOString() },
      { volume: 'II_PAST_PERFORMANCE', attachmentId: 'att-102', pageCount: 18, submittedAt: new Date().toISOString() },
      { volume: 'III_PRICE', attachmentId: 'att-103', pageCount: 10, submittedAt: new Date().toISOString() },
    ],
    submittedAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
    sealedUntil: new Date(Date.now() + 1000 * 60 * 60 * 24 * 14).toISOString(),
    amendmentAcks: [1],
  },
  {
    id: 'prop-003',
    foiaRequestId: 'sol-0142',
    vendorId: 'vnd-initech',
    vendorName: 'Initech Cloud Services',
    volumes: [
      { volume: 'I_TECHNICAL', attachmentId: 'att-201', pageCount: 55, submittedAt: new Date().toISOString() },
      { volume: 'II_PAST_PERFORMANCE', attachmentId: 'att-202', pageCount: 20, submittedAt: new Date().toISOString() },
      { volume: 'III_PRICE', attachmentId: 'att-203', pageCount: 11, submittedAt: new Date().toISOString() },
    ],
    submittedAt: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    sealedUntil: new Date(Date.now() + 1000 * 60 * 60 * 24 * 14).toISOString(),
    amendmentAcks: [],
  },
];

// ⚠ LEGACY (acquisition-era TEP) — feeds the inherited evaluator-workspace /
// consensus-ssdd demo only. The FOIA review fixtures are FIXTURE_REDACTION_REVIEWS.
export const FIXTURE_EVALUATION: LegacyTepReview = {
  id: 'eval-0142',
  foiaRequestId: 'foia-2026-0142',
  panelMembers: ['ev-allen', 'ev-mendez', 'ev-park'],
  factors: [
    { id: 'f-tech', name: 'Technical Approach', weight: 40, sectionM: 'M.3.1' },
    { id: 'f-mgmt', name: 'Management Approach', weight: 25, sectionM: 'M.3.2' },
    { id: 'f-pp', name: 'Past Performance', weight: 20, sectionM: 'M.3.3' },
    { id: 'f-price', name: 'Price (LPTA secondary)', weight: 15, sectionM: 'M.3.4' },
  ],
  state: 'INDIVIDUAL_SCORING',
  ssddDocId: null,
};

export const FIXTURE_SCORES: RedactionReviewScore[] = [
  { evaluatorId: 'ev-allen', evaluatorName: 'Dr. Allen', proposalId: 'prop-001', factorId: 'f-tech', score: 9, narrative: 'Strong zero-trust pattern; FedRAMP boundary clearly drawn.', submittedAt: new Date().toISOString() },
  { evaluatorId: 'ev-allen', evaluatorName: 'Dr. Allen', proposalId: 'prop-002', factorId: 'f-tech', score: 7, narrative: 'Acceptable approach; some risk on multi-cloud handoff.', submittedAt: new Date().toISOString() },
  { evaluatorId: 'ev-mendez', evaluatorName: 'A. Mendez', proposalId: 'prop-001', factorId: 'f-mgmt', score: 8, narrative: 'Clear PM org chart; key-personnel commitments solid.', submittedAt: new Date().toISOString() },
  { evaluatorId: 'ev-mendez', evaluatorName: 'A. Mendez', proposalId: 'prop-002', factorId: 'f-mgmt', score: 8, narrative: 'Comparable management; less depth on subcontractor mgmt.', submittedAt: new Date().toISOString() },
];

export const FIXTURE_AWARD: Award = {
  id: 'aw-2026-001',
  redactionReviewId: 'eval-0142',
  foiaRequestId: 'sol-0142',
  winningVendorId: 'vnd-acme',
  winningVendorName: 'Acme Federal LLC',
  contractNumber: 'GS-35F-0001V',
  awardedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
  ceilingValue: 110_000_000,
  debriefDeadline: new Date(Date.now() - 1000 * 60 * 60 * 24 * 25).toISOString(),
};

export const FIXTURE_MODIFICATIONS: ContractModification[] = [
  { id: 'mod-001', contractId: 'ctr-0001', modNumber: 'P00001', type: 'bilateral', changeDescription: 'Option year 1 exercise; ceiling delta +$18M.', effectiveAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 200).toISOString(), signedBy: 'co-reeves' },
  { id: 'mod-002', contractId: 'ctr-0001', modNumber: 'A00001', type: 'unilateral', changeDescription: 'Administrative — updated POC email after PM transition.', effectiveAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 120).toISOString(), signedBy: 'co-reeves' },
];

export const FIXTURE_DELIVERABLES: Deliverable[] = [
  { id: 'del-001', contractId: 'ctr-0001', cdrlNumber: 'A001', title: 'Monthly Status Report — May 2026', dueAt: new Date(Date.now() + 1000 * 60 * 60 * 24 * 5).toISOString(), status: 'PENDING', acceptedBy: null },
  { id: 'del-002', contractId: 'ctr-0001', cdrlNumber: 'A002', title: 'Q2 Security Compliance Attestation', dueAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(), status: 'SUBMITTED', acceptedBy: null },
  { id: 'del-003', contractId: 'ctr-0001', cdrlNumber: 'A003', title: 'Annual Cost Baseline Refresh', dueAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14).toISOString(), status: 'ACCEPTED', acceptedBy: 'co-reeves' },
];

export const FIXTURE_CPARS: Cpar[] = [
  {
    id: 'cpar-001',
    contractId: 'ctr-0001',
    period: 'INTERIM',
    ratings: [
      { factor: 'QUALITY', rating: 'VERY_GOOD', narrative: 'Deliverables consistently meet acceptance criteria.' },
      { factor: 'SCHEDULE', rating: 'SATISFACTORY', narrative: 'Two CDRLs slipped by less than 5 days each.' },
      { factor: 'COST_CONTROL', rating: 'VERY_GOOD', narrative: 'Burn rate within 3% of baseline.' },
      { factor: 'MANAGEMENT', rating: 'EXCEPTIONAL', narrative: 'Proactive risk communication; subcontractor mgmt strong.' },
      { factor: 'SMALL_BUSINESS', rating: 'SATISFACTORY', narrative: 'Met 23% small-business subcontracting target.' },
      { factor: 'REGULATORY_COMPLIANCE', rating: 'VERY_GOOD', narrative: 'FedRAMP continuous monitoring up to date.' },
    ],
    overallNarrative: 'Strong interim performance; ready to exercise option year 2.',
    vendorRebuttal: null,
    rebuttalDeadline: new Date(Date.now() + 1000 * 60 * 60 * 24 * 45).toISOString(),
    status: 'AWAITING_VENDOR_REVIEW',
  },
];

export const FIXTURE_VENDORS: Vendor[] = [
  {
    id: 'vnd-acme',
    duns: '123456789',
    uei: 'AB1CDE2FGHI3',
    cage: '7XYZ4',
    name: 'Acme Federal LLC',
    naicsCodes: ['541512', '541519'],
    setAsides: ['SMALL_BUSINESS', '8A'],
    registeredAt: '2018-04-12T00:00:00Z',
    pastPerformanceAvg: { exceptional: 4, veryGood: 11, satisfactory: 6, marginal: 1, unsatisfactory: 0, totalReports: 22 },
  },
  {
    id: 'vnd-globex',
    duns: '987654321',
    uei: 'ZX9YWV8UTSR7',
    cage: '4ABC2',
    name: 'Globex Federal Systems',
    naicsCodes: ['541511', '541512'],
    setAsides: ['FULL_AND_OPEN' as never],
    registeredAt: '2014-09-01T00:00:00Z',
    pastPerformanceAvg: { exceptional: 2, veryGood: 8, satisfactory: 12, marginal: 3, unsatisfactory: 1, totalReports: 26 },
  },
  {
    id: 'vnd-initech',
    duns: '555111222',
    uei: 'IN0TECHFGHIJ',
    cage: '9PQR5',
    name: 'Initech Cloud Services',
    naicsCodes: ['541519'],
    setAsides: ['SDVOSB'],
    registeredAt: '2020-01-15T00:00:00Z',
    pastPerformanceAvg: { exceptional: 0, veryGood: 3, satisfactory: 5, marginal: 2, unsatisfactory: 0, totalReports: 10 },
  },
];

export const FIXTURE_AUDIT_EVENTS: AuditEvent[] = [
  { id: 'ae-001', actorId: 'fo-reeves', actorName: 'Dana Reeves', agencyId: 'DOJ-OIP', action: 'FOIA_REQUEST.INTAKE', objectType: 'FoiaRequest', objectId: 'foia-2026-0142', correlationId: 'r-abc-001', before: null, after: { status: 'INTAKE_TRIAGE' }, ts: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14).toISOString() },
  { id: 'ae-002', actorId: 'fo-reeves', actorName: 'Dana Reeves', agencyId: 'DOJ-OIP', action: 'EXEMPTION.PROPOSE', objectType: 'RedactionReview', objectId: 'rr-0142', correlationId: 'r-abc-002', before: null, after: { exemptions: ['(b)(5)', '(b)(6)'] }, ts: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString() },
  { id: 'ae-003', actorId: 'gc-whitfield', actorName: 'Col. Whitfield', agencyId: 'DOJ-OIP', action: 'RELEASE.DETERMINE', objectType: 'RedactionReview', objectId: 'rr-0203', correlationId: 'r-def-001', before: { state: 'UNDER_REVIEW' }, after: { releaseDecision: 'release_partial' }, ts: new Date(Date.now() - 1000 * 60 * 60 * 22).toISOString() },
  { id: 'ae-004', actorId: 'gc-whitfield', actorName: 'Col. Whitfield', agencyId: 'DOJ-OIP', action: 'APPEAL.OPEN', objectType: 'FoiaRequest', objectId: 'foia-2026-0418', correlationId: 'r-ghi-001', before: { disposition: 'partial_grant' }, after: { status: 'APPEAL' }, ts: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString() },
];

export const FIXTURE_FINDINGS: Finding[] = [
  {
    id: 'F-2026-0007',
    scope: 'PLATFORM',
    scopeId: 'foia-response-pipeline',
    title: 'CI lint workflow disabled — repo-self finding',
    findingType: 'CA-7 continuous monitoring',
    severity: 'MODERATE',
    status: 'OPEN',
    openedBy: 'oig-park',
    openedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
    remediationDueAt: new Date(Date.now() + 1000 * 60 * 60 * 24 * 30).toISOString(),
    evidenceRequests: [
      { id: 'er-1', requestedBy: 'oig-park', requestedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(), description: 'Provide screenshot of re-enabled lint step in successful PR build.', fulfilledAt: null },
    ],
    description: 'Repository CI (`infra/github-actions/ci.yml`) skips lint with TODO. (Item 12 — meta-mirror per feature inventory.)',
  },
  {
    id: 'F-2026-0008',
    scope: 'CONTRACT',
    scopeId: 'ctr-0001',
    title: 'QASP findings ledger missing 2 entries for May surveillance',
    findingType: 'AU-12 audit record generation',
    severity: 'HIGH',
    status: 'IN_REMEDIATION',
    openedBy: 'oig-park',
    openedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14).toISOString(),
    remediationDueAt: new Date(Date.now() + 1000 * 60 * 60 * 24 * 10).toISOString(),
    evidenceRequests: [],
    description: 'AuditEvent gap suggests Item 2 race during high-load surveillance window.',
  },
];
