import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Qna } from '../models/qna';

@Injectable({ providedIn: 'root' })
export class QnaService {
  constructor(private http: HttpClient) {}

  list(foiaRequestId: string): Observable<Qna[]> {
    return this.http.get<Qna[]>(
      `${environment.apiGatewayUrl}/api/foia-requests/${foiaRequestId}/qa`,
    );
  }

  answer(foiaRequestId: string, qaId: string, answer: string): Observable<Qna> {
    return this.http.put<Qna>(
      `${environment.apiGatewayUrl}/api/foia-requests/${foiaRequestId}/qa/${qaId}/answer`,
      { answer },
    );
  }

  submitQuestion(foiaRequestId: string, question: string): Observable<Qna> {
    return this.http.post<Qna>(
      `${environment.apiGatewayUrl}/api/foia-requests/${foiaRequestId}/qa`,
      { question },
    );
  }
}
