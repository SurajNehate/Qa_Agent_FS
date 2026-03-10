import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  AskRequest,
  AskResponse,
  HealthResponse,
  IngestResponse,
  SessionResponse,
} from '../models/api.models';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  health(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.baseUrl}/api/health`);
  }

  ask(req: AskRequest): Observable<AskResponse> {
    return this.http.post<AskResponse>(`${this.baseUrl}/api/ask`, req);
  }

  ingest(files: File[], replaceExisting = false): Observable<IngestResponse> {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const params = replaceExisting ? '?replace_existing=true' : '';
    return this.http.post<IngestResponse>(
      `${this.baseUrl}/api/ingest${params}`,
      formData
    );
  }

  listSessions(): Observable<SessionResponse[]> {
    return this.http.get<SessionResponse[]>(`${this.baseUrl}/api/sessions`);
  }

  deleteSession(id: string): Observable<unknown> {
    return this.http.delete(`${this.baseUrl}/api/sessions/${id}`);
  }

  getSessionMessages(id: string): Observable<{ role: string; content: string }[]> {
    return this.http.get<{ role: string; content: string }[]>(
      `${this.baseUrl}/api/sessions/${id}/messages`
    );
  }

  clearIndex(): Observable<unknown> {
    return this.http.delete(`${this.baseUrl}/api/index`);
  }
}
