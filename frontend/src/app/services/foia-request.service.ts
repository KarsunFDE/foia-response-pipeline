import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { FoiaRequest, FoiaRequestCreate } from '../models/foia-request';

/**
 * FoiaRequest service — the "right" way to talk to the backend.
 *
 * Goes through the API gateway (environment.apiGatewayUrl). The cohort
 * compares this with `foiaRequest-list.component.ts`, which hardcodes
 * `http://localhost:8081` and bypasses the gateway (Item 8).
 */
@Injectable({ providedIn: 'root' })
export class FoiaRequestService {
  private readonly baseUrl = `${environment.apiGatewayUrl}/api/foia-requests`;

  constructor(private http: HttpClient) {}

  list(): Observable<FoiaRequest[]> {
    return this.http.get<FoiaRequest[]>(this.baseUrl);
  }

  get(id: string): Observable<FoiaRequest> {
    return this.http.get<FoiaRequest>(`${this.baseUrl}/${id}`);
  }

  create(req: FoiaRequestCreate): Observable<FoiaRequest> {
    return this.http.post<FoiaRequest>(this.baseUrl, req);
  }
}
