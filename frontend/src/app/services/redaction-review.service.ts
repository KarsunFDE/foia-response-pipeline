import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { RedactionReview, RedactionReviewScore } from '../models/redaction_review';

@Injectable({ providedIn: 'root' })
export class RedactionReviewService {
  constructor(private http: HttpClient) {}

  get(id: string): Observable<RedactionReview> {
    return this.http.get<RedactionReview>(
      `${environment.apiGatewayUrl}/api/redaction-reviews/${id}`,
    );
  }

  scores(id: string): Observable<RedactionReviewScore[]> {
    return this.http.get<RedactionReviewScore[]>(
      `${environment.apiGatewayUrl}/api/redaction-reviews/${id}/scores`,
    );
  }

  submitScore(id: string, score: Partial<RedactionReviewScore>): Observable<RedactionReviewScore> {
    return this.http.post<RedactionReviewScore>(
      `${environment.apiGatewayUrl}/api/redaction-reviews/${id}/scores`,
      score,
    );
  }

  consensus(id: string): Observable<RedactionReviewScore[]> {
    return this.http.get<RedactionReviewScore[]>(
      `${environment.apiGatewayUrl}/api/redaction-reviews/${id}/consensus`,
    );
  }

  /** AI-drafted Source Selection Decision Document narrative (FAR 15.308). */
  draftSsdd(id: string): Observable<{ narrative: string; correlationId: string }> {
    return this.http.post<{ narrative: string; correlationId: string }>(
      `${environment.apiGatewayUrl}/api/ai/eval/ssdd-draft`,
      { redaction_reviewId: id },
    );
  }
}
