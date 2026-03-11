import { Injectable, NgZone } from '@angular/core';
import { Observable } from 'rxjs';
import { AskRequest, Citation } from '../models/api.models';
import { environment } from '../../../environments/environment';

export interface StreamEvent {
  type: 'token' | 'meta' | 'done';
  token?: string;
  citations?: Citation[];
  source_type?: string;
  model?: string;
  used_fallback?: boolean;
  session_id?: string;
}

@Injectable({ providedIn: 'root' })
export class StreamService {
  private baseUrl = environment.apiUrl;

  constructor(private ngZone: NgZone) {}

  /**
   * Consume SSE stream from /api/ask/stream.
   * Emits StreamEvent objects — tokens during stream, metadata at end.
   */
  askStream(req: AskRequest): Observable<StreamEvent> {
    return new Observable((observer) => {
      const abortController = new AbortController();

      fetch(`${this.baseUrl}/api/ask/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
        signal: abortController.signal,
      })
        .then((response) => {
          if (!response.ok) {
            this.ngZone.run(() => observer.error(new Error(`HTTP ${response.status}`)));
            return;
          }
          const reader = response.body!.getReader();
          const decoder = new TextDecoder();

          const read = (): void => {
            reader.read().then(({ done, value }) => {
              if (done) {
                this.ngZone.run(() => observer.complete());
                return;
              }
              const text = decoder.decode(value, { stream: true });
              const lines = text.split('\n');
              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const data = line.slice(6);

                  if (data === '[DONE]') {
                    this.ngZone.run(() => {
                      observer.next({ type: 'done' });
                      observer.complete();
                    });
                    return;
                  }

                  if (data.startsWith('[META]')) {
                    try {
                      const meta = JSON.parse(data.slice(6));
                      this.ngZone.run(() => observer.next({
                        type: 'meta',
                        citations: meta.citations,
                        source_type: meta.source_type,
                        model: meta.model,
                        used_fallback: meta.used_fallback,
                        session_id: meta.session_id,
                      }));
                    } catch {
                      // ignore malformed meta
                    }
                    continue;
                  }

                  // Regular token (JSON encoded from backend to preserve newlines)
                  try {
                    const parsedToken = JSON.parse(data);
                    this.ngZone.run(() => observer.next({ type: 'token', token: parsedToken }));
                  } catch {
                    // Fallback for older backend versions
                    this.ngZone.run(() => observer.next({ type: 'token', token: data }));
                  }
                }
              }
              read();
            });
          };
          read();
        })
        .catch((err) => {
          if (err.name !== 'AbortError') {
            this.ngZone.run(() => observer.error(err));
          }
        });

      return () => abortController.abort();
    });
  }
}
