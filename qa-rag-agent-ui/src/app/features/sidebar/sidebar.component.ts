import { Component, OnInit, Output, EventEmitter, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { SessionResponse, HealthResponse, ModelInfo } from '../../core/models/api.models';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent implements OnInit {
  @Output() sessionSelected = new EventEmitter<string>();
  @Output() settingsChanged = new EventEmitter<{ rag: boolean; tools: boolean }>();
  @Output() modelChanged = new EventEmitter<string>();
  @Output() newChat = new EventEmitter<void>();

  sessions: SessionResponse[] = [];
  health: HealthResponse | null = null;
  ragEnabled = true;
  toolsEnabled = false;
  selectedFiles: File[] = [];
  uploadStatus = '';
  isUploading = false;
  isCollapsed = false;

  // LLM Model — fetched from /api/models
  selectedModel = '';
  models: ModelInfo[] = [];

  constructor(
    private apiService: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadHealth();
    this.loadSessions();
    this.loadModels();
  }

  loadHealth(): void {
    this.apiService.health().subscribe({
      next: (h) => {
        this.health = h;
        this.cdr.detectChanges();
      },
      error: () => {
        this.health = null;
        this.cdr.detectChanges();
      },
    });
  }

  loadModels(): void {
    this.apiService.getModels().subscribe({
      next: (models) => {
        this.models = models;
        const defaultModel = models.find((m) => m.is_default);
        if (defaultModel) {
          this.selectedModel = defaultModel.model;
        } else if (models.length > 0) {
          this.selectedModel = models[0].model;
        }
        this.cdr.detectChanges();
      },
      error: () => {
        this.models = [];
        this.cdr.detectChanges();
      },
    });
  }

  loadSessions(): void {
    this.apiService.listSessions().subscribe({
      next: (s) => {
        this.sessions = s;
        this.cdr.detectChanges();
      },
      error: () => {
        this.sessions = [];
        this.cdr.detectChanges();
      },
    });
  }

  selectSession(id: string): void {
    this.sessionSelected.emit(id);
  }

  onNewChat(): void {
    this.newChat.emit();
  }

  deleteSession(id: string, event: Event): void {
    event.stopPropagation();
    this.apiService.deleteSession(id).subscribe({
      next: () => {
        this.sessions = this.sessions.filter((s) => s.id !== id);
        this.cdr.detectChanges();
      },
    });
  }

  onSettingsChange(): void {
    this.settingsChanged.emit({
      rag: this.ragEnabled,
      tools: this.toolsEnabled,
    });
  }

  onModelChange(): void {
    this.modelChanged.emit(this.selectedModel);
  }

  getModelLabel(m: ModelInfo): string {
    const provLabel = m.provider.charAt(0).toUpperCase() + m.provider.slice(1);
    return `${m.model} (${provLabel})`;
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.selectedFiles = Array.from(input.files);
    }
  }

  uploadFiles(): void {
    if (!this.selectedFiles.length) return;
    this.isUploading = true;
    this.uploadStatus = 'Uploading...';
    this.cdr.detectChanges();

    this.apiService.ingest(this.selectedFiles).subscribe({
      next: (res) => {
        this.uploadStatus = `✅ ${res.files_processed} files → ${res.chunks_created} chunks`;
        this.selectedFiles = [];
        this.isUploading = false;
        this.cdr.detectChanges();
        this.loadHealth();
      },
      error: (err) => {
        this.uploadStatus = '❌ Upload failed';
        this.isUploading = false;
        this.cdr.detectChanges();
        console.error('Upload error:', err);
      },
    });
  }

  clearIndex(): void {
    if (!confirm('Clear all indexed documents? This cannot be undone.')) return;
    this.apiService.clearIndex().subscribe({
      next: () => {
        this.uploadStatus = '🗑️ Index cleared';
        this.cdr.detectChanges();
        this.loadHealth();
      },
      error: () => {
        this.uploadStatus = '❌ Failed to clear index';
        this.cdr.detectChanges();
      },
    });
  }

  toggleSidebar(): void {
    this.isCollapsed = !this.isCollapsed;
    this.cdr.detectChanges();
  }
}
