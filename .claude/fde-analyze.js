export const meta = {
  name: 'fde-analyze',
  description: 'FDE codebase analysis arm: exhaustive cited read of the whole repo via blind dual-analyst fan-out, reconciled, clustered by business capability, scope-tagged for an Angular -> React/Next.js modernization. Reads only; writes nothing to the repo; returns one analysis report.',
  whenToUse: 'Run before modernizing a legacy codebase to get a verified, evidence-cited map of features, data/schema, business rules, personas, debt, security, and modernization scope. Pairs with /fde-plan (the planning arm) which runs after a target is chosen.',
  phases: [
    { title: 'Load' },
    { title: 'Discover' },
    { title: 'Read' },
    { title: 'Reconcile' },
    { title: 'Merge' },
    { title: 'Scope' },
    { title: 'Report' },
  ],
};

// ───────────────────────── SCHEMAS ─────────────────────────
const WORKLIST = {
  type: 'object',
  required: ['files'],
  properties: {
    files: { type: 'array', items: { type: 'string' }, description: 'Every source/config/schema file path in the repo' },
    excluded: { type: 'array', items: { type: 'string' }, description: 'Globs excluded (vendored/build dirs) and why' },
    total: { type: 'number' },
  },
};

const FINDINGS = {
  type: 'object',
  required: ['file', 'readInFull', 'findings'],
  properties: {
    file: { type: 'string' },
    readInFull: { type: 'boolean', description: 'true only if the entire file was read, no skimming' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'lineStart', 'lineEnd', 'type', 'category', 'evidence_type', 'confidence'],
        properties: {
          claim: { type: 'string' },
          lineStart: { type: 'number' },
          lineEnd: { type: 'number' },
          type: { type: 'string', enum: ['feature', 'data', 'rule', 'flow', 'service', 'debt', 'security', 'persona', 'integration'] },
          category: { type: 'string', enum: ['fact', 'inference', 'recommendation'] },
          evidence_type: { type: 'string', enum: ['code', 'comment-only'] },
          confidence: { type: 'number' },
          note: { type: 'string' },
        },
      },
    },
  },
};

const RECONCILED = {
  type: 'object',
  required: ['file', 'confirmed', 'conflicts', 'onlyOne'],
  properties: {
    file: { type: 'string' },
    confirmed: { type: 'array', items: { type: 'object' }, description: 'findings both analysts agree on' },
    conflicts: { type: 'array', items: { type: 'object' }, description: 'disagreements, resolved by re-reading the cited lines' },
    onlyOne: { type: 'array', items: { type: 'object' }, description: 'found by only A or only B — coverage gaps' },
    agreement: { type: 'number', description: '0-1 share of findings both analysts independently agreed on' },
  },
};

const CLUSTERS = {
  type: 'object',
  required: ['capabilities', 'duplications', 'ghosts'],
  properties: {
    capabilities: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'criticality'],
        properties: {
          name: { type: 'string' },
          description: { type: 'string' },
          supporting: { type: 'array', items: { type: 'string' }, description: 'cited services/data/workflows file:line' },
          users: { type: 'array', items: { type: 'string' } },
          businessValue: { type: 'string' },
          criticality: { type: 'string', enum: ['Critical', 'High', 'Medium', 'Low'] },
          whatBreaksIfRemoved: { type: 'string' },
          confidence: { type: 'number' },
        },
      },
    },
    duplications: { type: 'array', items: { type: 'object' }, description: 'logic repeated across files, with duplicated_at lists' },
    ghosts: { type: 'array', items: { type: 'object' }, description: 'comment-only references, demoted' },
  },
};

const SCHEMA_MAP = {
  type: 'object',
  required: ['entities', 'orphanedSchemas', 'missingSchemas'],
  properties: {
    entities: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          entity: { type: 'string' },
          fields: { type: 'array', items: { type: 'object' } },
          source: { type: 'string', enum: ['explicit', 'reconstructed'] },
          definedAt: { type: 'string' },
        },
      },
    },
    orphanedSchemas: { type: 'array', items: { type: 'string' } },
    missingSchemas: { type: 'array', items: { type: 'string' } },
  },
};

const PERSONAS = {
  type: 'object',
  required: ['personas'],
  properties: {
    personas: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'confidence', 'corroboration'],
        properties: {
          name: { type: 'string' },
          confidence: { type: 'number' },
          evidence: { type: 'array', items: { type: 'string' }, description: 'file:line citations' },
          corroboration: { type: 'string', enum: ['code+claudemd', 'code-only', 'claudemd-only', 'readme-only'] },
          goals: { type: 'string' },
          responsibilities: { type: 'string' },
          painPoints: { type: 'string' },
        },
      },
    },
  },
};

const SCOPED = {
  type: 'object',
  required: ['scoped'],
  properties: {
    scoped: {
      type: 'array',
      items: {
        type: 'object',
        required: ['capability', 'scope'],
        properties: {
          capability: { type: 'string' },
          scope: { type: 'string', enum: ['in-scope', 'out-of-scope', 'boundary'] },
          rationale: { type: 'string' },
          boundaryContract: { type: 'string', description: 'for boundary items: the contract that must hold across migration' },
        },
      },
    },
  },
};

// ───────────────────────── RULES (inlined so agents obey even if skills are not auto-loaded) ─────────────────────────
const EVIDENCE_RULES = `
Follow the fde-evidence-rules skill. Core rules:
- Cite file:line for every claim; no citation => drop the finding.
- Tag each finding category: fact (observable at the line) | inference (reasoned) | recommendation.
- Tag evidence_type: code | comment-only. A claim supported only by comments is a GHOST -> mark it, never assert as real.
- confidence 0.0-1.0 (facts = 1.0; inferences scored by strength/corroboration; explain why).
- Read the ENTIRE assigned file before emitting any finding. No skimming. No guessing about unread regions.`;

// ───────────────────────── WORKFLOW ─────────────────────────

// Ph0 LOAD — read this repo's personas (CLAUDE.md) + optional config. Personas are per-repo, not baked.
phase('Load');
const cfg = await agent(
  `Read the repository's CLAUDE.md (and ./fde.config.md if it exists). Extract the project's curated personas
   (name + the file:line evidence each cites) and any domain glossary. If neither file exists, return empty personas.
   Return only what the files state — do not invent personas.`,
  { label: 'load-config', phase: 'Load', schema: PERSONAS, agentType: 'Explore' }
);
const knownPersonas = (cfg && cfg.personas) || [];
log(`Loaded ${knownPersonas.length} curated persona(s) from CLAUDE.md.`);

// Ph1 DISCOVER — filesystem walk (NOT import-graph) so no domain goes invisible.
phase('Discover');
const work = await agent(
  `Enumerate EVERY source, config, schema, and infrastructure file in this repository via a filesystem walk
   (e.g. \`git ls-files\`). Do NOT seed from entrypoints or imports — a disconnected domain must still appear.
   Exclude only vendored/build/generated dirs (node_modules, dist, build, .git, target, __pycache__, .venv) and
   record what you excluded. Return the full file list and the total count.`,
  { label: 'discover-files', phase: 'Discover', schema: WORKLIST, agentType: 'Explore' }
);
const files = (work && work.files) || [];
log(`Discovered ${files.length} files. Excluded: ${((work && work.excluded) || []).join(', ') || 'none'}.`);

// Ph2+3 READ + RECONCILE — per file: two BLIND analysts (A,B) read in full, then adjudicate.
// Pipeline (no global barrier): each file is read+reconciled independently and concurrently.
phase('Read');
const analystPrompt = (file, tag) => `
You are independent analyst ${tag}. You have NOT seen any other analyst's work — do not assume one exists.
Read the file ${file} IN FULL. Extract everything that exists: features, data models, business rules/constraints,
flows, services, integrations, technical debt, security concerns, and any stakeholder/persona signals
(roles, permissions, route names, regulation references like FAR clauses, audit actors).
${EVIDENCE_RULES}
Set readInFull=true only if you read the whole file. Return findings for ${file} only.`;

const perFile = await pipeline(
  files,
  // stage 1 — blind A + B (parallel, neither sees the other)
  (file) =>
    parallel([
      () => agent(analystPrompt(file, 'A'), { label: `A:${file}`, phase: 'Read', schema: FINDINGS }),
      () => agent(analystPrompt(file, 'B'), { label: `B:${file}`, phase: 'Read', schema: FINDINGS }),
    ]).then(([a, b]) => ({ file, a, b })),
  // stage 2 — adjudicator reconciles A vs B; RE-READS disputed lines
  (pair) =>
    agent(
      `Adjudicate two independent blind analyses of ${pair.file}.
       Analyst A: ${JSON.stringify(pair.a)}
       Analyst B: ${JSON.stringify(pair.b)}
       - Findings both report (same file:line + same claim) => confirmed (high confidence).
       - Findings that CONFLICT => RE-READ the exact cited lines in ${pair.file} and resolve; record resolution.
       - Findings only one analyst reported => onlyOne (a coverage gap to surface, do not silently drop).
       Compute an agreement score (0-1). ${EVIDENCE_RULES}`,
      { label: `adj:${pair.file}`, phase: 'Reconcile', schema: RECONCILED }
    )
);

const reconciled = perFile.filter(Boolean);
const readSet = reconciled.map((r) => r.file);
const allConfirmed = reconciled.flatMap((r) => [...(r.confirmed || []), ...(r.onlyOne || [])]);
log(`Read + reconciled ${readSet.length}/${files.length} files; ${allConfirmed.length} findings.`);

// Ph4 MERGE — cross-file barrier: clustering, schema map, persona synthesis run together (each needs ALL findings).
phase('Merge');
const findingsBlob = JSON.stringify(allConfirmed).slice(0, 500000);
const [clusters, schemaMap, personas] = await parallel([
  () =>
    agent(
      `Use the capability-clustering skill. Group these cited findings into business capabilities, detect
       duplication across files (duplicated_at), demote comment-only ghosts, and score criticality.
       Findings: ${findingsBlob}`,
      { label: 'cluster', phase: 'Merge', schema: CLUSTERS }
    ),
  () =>
    agent(
      `Use the schema-extraction skill. Build the schema map from these findings and the file list.
       Classify schema-defining vs data-bearing; if no schema files exist, reconstruct entity shape from code
       (models/interfaces/forms), cite file:line, mark source=reconstructed. Flag orphaned + missing schemas.
       Findings: ${findingsBlob}
       Files: ${JSON.stringify(files).slice(0, 50000)}`,
      { label: 'schema-map', phase: 'Merge', schema: SCHEMA_MAP }
    ),
  () =>
    agent(
      `Use the persona-synthesis skill. From the persona-type findings, discover the stakeholders of this system.
       Corroborate each against the curated CLAUDE.md personas below: code+CLAUDE.md => confirmed; CLAUDE.md/README only
       => ghost; code only => propose as new. Score confidence with file:line evidence.
       Curated personas: ${JSON.stringify(knownPersonas)}
       Persona findings: ${JSON.stringify(allConfirmed.filter((f) => f && f.type === 'persona')).slice(0, 100000)}`,
      { label: 'personas', phase: 'Merge', schema: PERSONAS }
    ),
]);

// Ph5 SCOPE — tag each capability for the Angular -> React/Next.js modernization.
phase('Scope');
const scoped = await agent(
  `For an Angular -> React/Next.js FRONTEND modernization, tag each capability:
   - in-scope (frontend that migrates), out-of-scope (backend/infra — mapped, not touched),
   - boundary (talks to in-scope; its contract MUST hold across the migration — name the contract).
   Capabilities: ${JSON.stringify((clusters && clusters.capabilities) || []).slice(0, 200000)}`,
  { label: 'scope', phase: 'Scope', schema: SCOPED }
);

// Ph6 COMPLETENESS — deterministic gate: which work-list files were never read?
const readLookup = new Set(readSet);
const missed = files.filter((f) => !readLookup.has(f));
const coveragePct = files.length ? Math.round(((files.length - missed.length) / files.length) * 100) : 100;
if (missed.length) log(`COVERAGE GAP: ${missed.length} file(s) not read — ${coveragePct}%. They will be listed in the report.`);
else log(`Total coverage: ${files.length}/${files.length} files read (100%).`);

// Ph7 REPORT — synthesize the analysis report. Returned to the session; NOT written into the repo.
phase('Report');
const agreementScores = reconciled.map((r) => r.agreement).filter((x) => typeof x === 'number');
const avgAgreement = agreementScores.length
  ? (agreementScores.reduce((a, b) => a + b, 0) / agreementScores.length).toFixed(2)
  : 'n/a';

const report = await agent(
  `Write the FDE Analysis Report as professional Markdown. Follow the fde-evidence-rules skill:
   separate FACTS / INFERENCES / RECOMMENDATIONS and show confidence scores throughout.

   Required sections:
   1. Executive Summary — what the system does, why it exists, who uses it.
   2. Capability Map — clusters with criticality + what-breaks-if-removed.
   3. Personas — discovered stakeholders, evidence, confidence, corroboration vs CLAUDE.md.
   4. Schema Map — markdown table (entity|field|type|constraint|file:line|source) + orphaned/missing lists.
   5. Duplication & Ghosts — repeated logic and comment-only references.
   6. Modernization Scope Map — in-scope / out-of-scope / boundary (with boundary contracts).
   7. Reliability — dual-analyst average agreement: ${avgAgreement}. Coverage: ${coveragePct}% (${files.length - missed.length}/${files.length}).
      List every missed file with a reason (NO silent truncation): ${JSON.stringify(missed).slice(0, 20000)}
   8. Modernization Options — PRESENT React vs Next.js profiles for the in-scope frontend. DO NOT pick one
      (the workflow cannot wait for input mid-run; selection happens by invoking /fde-plan <target> afterward).

   Inputs:
   capabilities=${JSON.stringify((clusters && clusters.capabilities) || []).slice(0, 150000)}
   duplications=${JSON.stringify((clusters && clusters.duplications) || []).slice(0, 40000)}
   ghosts=${JSON.stringify((clusters && clusters.ghosts) || []).slice(0, 40000)}
   personas=${JSON.stringify((personas && personas.personas) || []).slice(0, 60000)}
   schema=${JSON.stringify(schemaMap || {}).slice(0, 80000)}
   scope=${JSON.stringify((scoped && scoped.scoped) || []).slice(0, 80000)}`,
  { label: 'report', phase: 'Report' }
);

log('Analysis complete. Report returned to the session — review, then run /fde-plan <react|nextjs>.');
return report;
