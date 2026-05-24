import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Amendment, AmendmentCreate } from '../models/amendment';

/**
 * Amendments to a published foia_request (FAR 15.206).
 *
 * Routes through `environment.apiGatewayUrl` — the right way. Compare
 * with `foia_request-list.component.ts` which hardcodes :8081 per Item 8.
 */
@Injectable({ providedIn: 'root' })
export class AmendmentService {
  constructor(private http: HttpClient) {}

  list(foia_requestId: string): Observable<Amendment[]> {
    return this.http.get<Amendment[]>(
      `${environment.apiGatewayUrl}/api/foia-requests/${foia_requestId}/amendments`,
    );
  }

  issue(foia_requestId: string, req: AmendmentCreate): Observable<Amendment> {
    return this.http.post<Amendment>(
      `${environment.apiGatewayUrl}/api/foia-requests/${foia_requestId}/amendments`,
      req,
    );
  }
}
