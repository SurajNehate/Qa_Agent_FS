import { Component, OnInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { StreamService } from '../../core/services/stream.service';
import { ChatMessage, AskRequest, Citation } from '../../core/models/api.models';

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

  @Output() sessionCreated = new EventEmitter<void>();

  private streamSub?: Subscription;

  @ViewChild('chatContainer') chatContainer!: ElementRef;

  constructor(
    private apiService: ApiService,
    private streamService: StreamService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.addWelcomeMessage();
  }

  ngOnDestroy(): void {
    this.streamSub?.unsubscribe();
  }

  sendMessage(): void {
    const question = this.inputText.trim();
    if (!question || this.isLoading) return;

    // Add user message
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
    this.addWelcomeMessage();
  }

  getSourceBadge(sourceType?: string): string {
    switch (sourceType) {
      case 'rag': return '📚 RAG';
      case 'web': return '🌐 Web';
      case 'direct': return '💬 Direct';
      case 'fallback': return '⚠️ Fallback';
      default: return '';
    }
  }

  updateSettings(rag: boolean, tools: boolean): void {
    this.ragEnabled = rag;
    this.toolsEnabled = tools;
  }

  loadSession(sessionId: string): void {
    this.sessionId = sessionId;
    this.messages = [];

    // Load old messages from this session
    this.apiService.getSessionMessages(sessionId).subscribe({
      next: (msgs) => {
        this.messages = msgs.map((m) => ({
          role: m.role === 'human' ? 'user' as const : 'assistant' as const,
          content: m.content,
          timestamp: new Date(),
        }));
        this.cdr.detectChanges();
        this.scrollToBottom();
      },
      error: () => {
        // If loading fails, just show welcome message
        this.addWelcomeMessage();
        this.cdr.detectChanges();
      },
    });
  }

  private sendStreaming(req: AskRequest): void {
    const assistantMsg: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };
    this.messages.push(assistantMsg);
    this.scrollToBottom();

    this.streamSub = this.streamService.askStream(req).subscribe({
      next: (event) => {
        if (event.type === 'token' && event.token) {
          assistantMsg.content += event.token;
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
          citations: res.citations,
          source_type: res.source_type,
          timestamp: new Date(),
        });
        this.isLoading = false;
        this.scrollToBottom();
      },
      error: (err) => {
        this.messages.push({
          role: 'assistant',
          content: '⚠️ Error: Could not reach the server.',
          timestamp: new Date(),
        });
        this.isLoading = false;
        console.error('API error:', err);
      },
    });
  }

  private addWelcomeMessage(): void {
    this.messages.push({
      role: 'assistant',
      content:
        'Hello! I\'m the **QA RAG Agent**. Ask me anything about your indexed documents, or enable tools for web search capabilities.',
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
