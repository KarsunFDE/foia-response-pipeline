import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  ClauseSearchResult,
  IntakeTriageRequest,
  TriageResult,
  TriageResumeRequest,
} from '../models/triage';

/**
 * AgentService — the agentic FOIA triage + RAG surface (ADR 0005).
 *
 * Routes through the API gateway (environment.apiGatewayUrl) under /api/ai,
 * which the gateway forwards to the ai-orchestrator (stripPrefix(2)):
 *   /api/ai/agent/intake-triage         → orchestrator /agent/intake-triage
 *   /api/ai/agent/intake-triage/resume  → orchestrator /agent/intake-triage/resume
 *   /api/ai/rag/clause-search           → orchestrator /rag/clause-search
 *
 * This is the "right way" (gateway-fronted) — contrast with the legacy
 * foiaRequest-list component that hardcodes a service URL (Item 8).
 */
@Injectable({ providedIn: 'root' })
export class AgentService {
  private readonly aiUrl = `${environment.apiGatewayUrl}/api/ai`;

  constructor(private http: HttpClient) {}

  /** Start the LangGraph triage pipeline; pauses at the first HITL gate. */
  startTriage(req: IntakeTriageRequest): Observable<TriageResult> {
    return this.http.post<TriageResult>(`${this.aiUrl}/agent/intake-triage`, req);
  }

  /** Resume a paused run with a human reviewer's gate decision. */
  resumeTriage(req: TriageResumeRequest): Observable<TriageResult> {
    return this.http.post<TriageResult>(`${this.aiUrl}/agent/intake-triage/resume`, req);
  }

  /** Hybrid RAG over the FOIA precedent corpus (5 USC 552 / 28 CFR 16). */
  clauseSearch(
    query: string,
    opts: { far_part?: string | null; agency_id?: string | null; top_k?: number } = {},
  ): Observable<ClauseSearchResult> {
    return this.http.post<ClauseSearchResult>(`${this.aiUrl}/rag/clause-search`, {
      query,
      far_part: opts.far_part ?? null,
      agency_id: opts.agency_id ?? null,
      top_k: opts.top_k ?? 5,
    });
  }
}
