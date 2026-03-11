import {
  Component,
  OnInit,
  OnDestroy,
  ViewChild,
  ElementRef,
  ChangeDetectorRef,
  Output,
  EventEmitter,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer } from '@angular/platform-browser';
import { Subscription } from 'rxjs';
import { marked } from 'marked';
import { ApiService } from '../../core/services/api.service';
import { StreamService } from '../../core/services/stream.service';
import { ChatMessage, AskRequest } from '../../core/models/api.models';

/**
 * Chat component — handles message display, user input, and streaming.
 *
 * Markdown is parsed directly in the component logic. This provides
 * robust, bulletproof rendering during streaming updates, avoiding
 * Angular Change Detection caveats with pipes in @for loops.
 */
@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
})
export class ChatComponent implements OnInit, OnDestroy {
  messages: ChatMessage[] = [];
  inputText = '';
  isLoading = false;
  ragEnabled = true;
  toolsEnabled = false;
  sessionId: string | undefined;
  useStreaming = true;
  selectedModel: string | undefined;

  @Output() sessionCreated = new EventEmitter<void>();

  @ViewChild('chatContainer') chatContainer!: ElementRef;

  private streamSub?: Subscription;

  constructor(
    private apiService: ApiService,
    private streamService: StreamService,
    private cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer,
  ) {
    marked.setOptions({ breaks: true, gfm: true });
  }

  ngOnInit(): void {
    this.addWelcomeMessage();
  }

  ngOnDestroy(): void {
    this.streamSub?.unsubscribe();
  }

  // ── Public API (called from parent / template) ───────────────

  sendMessage(): void {
    const question = this.inputText.trim();
    if (!question || this.isLoading) return;

    this.messages.push({
      role: 'user',
      content: question,
      timestamp: new Date(),
    });
    this.inputText = '';
    this.isLoading = true;
    this.scrollToBottom();

    const req: AskRequest = {
      question,
      rag_enabled: this.ragEnabled,
      tools_enabled: this.toolsEnabled,
      session_id: this.sessionId,
      model: this.selectedModel,
    };

    if (this.useStreaming) {
      this.sendStreaming(req);
    } else {
      this.sendNonStreaming(req);
    }
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  clearChat(): void {
    this.messages = [];
    this.sessionId = undefined;
    this.addWelcomeMessage();
  }

  getSourceBadge(sourceType?: string): string {
    switch (sourceType) {
      case 'rag':
        return '📚 RAG';
      case 'web':
        return '🌐 Web';
      case 'direct':
        return '💬 Direct';
      case 'fallback':
        return '⚠️ Fallback';
      default:
        return '';
    }
  }

  updateSettings(rag: boolean, tools: boolean): void {
    this.ragEnabled = rag;
    this.toolsEnabled = tools;
  }

  /** Load messages from a previous session. */
  loadSession(sessionId: string): void {
    this.sessionId = sessionId;
    this.messages = [];

    this.apiService.getSessionMessages(sessionId).subscribe({
      next: (msgs) => {
        this.messages = msgs.map((m) => {
          const role = m.role === 'human' ? 'user' : 'assistant';
          const msg: ChatMessage = {
            role,
            content: m.content,
            timestamp: new Date(),
          };
          if (role === 'assistant') {
            msg.renderedHtml = this.parseMarkdown(m.content);
          }
          return msg;
        });
        this.cdr.detectChanges();
        this.scrollToBottom();
      },
      error: () => {
        this.addWelcomeMessage();
      },
    });
  }

  // ── Private helpers ──────────────────────────────────────────

  /** Parses markdown string and returns SafeHtml. */
  private parseMarkdown(text: string): any {
    if (!text) return '';
    const html = marked.parse(text) as string;
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  /**
   * Stream tokens from the server, appending each to the assistant
   * message in real-time. Markdown is re-parsed on each token.
   */
  private sendStreaming(req: AskRequest): void {
    const assistantMsg: ChatMessage = {
      role: 'assistant',
      content: '',
      renderedHtml: '',
      timestamp: new Date(),
      isStreaming: true,
    };
    this.messages.push(assistantMsg);
    this.scrollToBottom();

    this.streamSub = this.streamService.askStream(req).subscribe({
      next: (event) => {
        if (event.type === 'token' && event.token) {
          assistantMsg.content += event.token;
          // Pre-render HTML for bulletproof Angular binding
          assistantMsg.renderedHtml = this.parseMarkdown(assistantMsg.content);
          this.cdr.detectChanges();
          this.scrollToBottom();
        } else if (event.type === 'meta') {
          assistantMsg.source_type = event.source_type;
          assistantMsg.citations = event.citations;
          if (event.session_id && !this.sessionId) {
            this.sessionId = event.session_id;
            this.sessionCreated.emit();
          }
          this.cdr.detectChanges();
        }
      },
      error: (err) => {
        assistantMsg.content += '\n\n⚠️ Error: Could not reach the server.';
        assistantMsg.renderedHtml = this.parseMarkdown(assistantMsg.content);
        assistantMsg.isStreaming = false;
        this.isLoading = false;
        this.cdr.detectChanges();
        console.error('Stream error:', err);
      },
      complete: () => {
        assistantMsg.isStreaming = false;
        this.isLoading = false;
        this.cdr.detectChanges();
        this.scrollToBottom();
      },
    });
  }

  private sendNonStreaming(req: AskRequest): void {
    this.apiService.ask(req).subscribe({
      next: (res) => {
        if (res.session_id && !this.sessionId) {
          this.sessionId = res.session_id;
          this.sessionCreated.emit();
        }
        this.messages.push({
          role: 'assistant',
          content: res.answer,
          renderedHtml: this.parseMarkdown(res.answer),
          citations: res.citations,
          source_type: res.source_type,
          timestamp: new Date(),
        });
        this.isLoading = false;
        this.scrollToBottom();
      },
      error: (err) => {
        const errorContent = '⚠️ Error: Could not reach the server.';
        this.messages.push({
          role: 'assistant',
          content: errorContent,
          renderedHtml: this.parseMarkdown(errorContent),
          timestamp: new Date(),
        });
        this.isLoading = false;
        console.error('API error:', err);
      },
    });
  }

  private addWelcomeMessage(): void {
    const content = "Hello! I'm the **QA RAG Agent**. Ask me anything about your indexed documents, or enable tools for web search capabilities.";
    this.messages.push({
      role: 'assistant',
      content,
      renderedHtml: this.parseMarkdown(content),
      timestamp: new Date(),
    });
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      if (this.chatContainer) {
        const el = this.chatContainer.nativeElement;
        el.scrollTop = el.scrollHeight;
      }
    }, 50);
  }
}
