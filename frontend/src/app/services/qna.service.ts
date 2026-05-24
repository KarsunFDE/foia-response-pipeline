import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Qna } from '../models/qna';

@Injectable({ providedIn: 'root' })
export class QnaService {
  constructor(private http: HttpClient) {}

  list(foia_requestId: string): Observable<Qna[]> {
    return this.http.get<Qna[]>(
      `${environment.apiGatewayUrl}/api/foia-requests/${foia_requestId}/qa`,
    );
  }

  answer(foia_requestId: string, qaId: string, answer: string): Observable<Qna> {
    return this.http.put<Qna>(
      `${environment.apiGatewayUrl}/api/foia-requests/${foia_requestId}/qa/${qaId}/answer`,
      { answer },
    );
  }

  submitQuestion(foia_requestId: string, question: string): Observable<Qna> {
    return this.http.post<Qna>(
      `${environment.apiGatewayUrl}/api/foia-requests/${foia_requestId}/qa`,
      { question },
    );
  }
}
