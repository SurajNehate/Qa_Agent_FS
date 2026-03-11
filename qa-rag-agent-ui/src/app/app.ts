import { Component, ViewChild } from '@angular/core';
import { SidebarComponent } from './features/sidebar/sidebar.component';
import { ChatComponent } from './features/chat/chat.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [SidebarComponent, ChatComponent],
  template: `
    <div class="app-layout">
      <!-- Overlay to close sidebar on mobile -->
      @if (isMobile() && !sidebar.isCollapsed) {
        <div class="mobile-overlay" (click)="sidebar.toggleSidebar()"></div>
      }
      <app-sidebar #sidebar
        (sessionSelected)="onSessionSelected($event); closeSidebarOnMobile(sidebar)"
        (settingsChanged)="onSettingsChanged($event)"
        (modelChanged)="onModelChanged($event)"
        (newChat)="onNewChat(); closeSidebarOnMobile(sidebar)"
      ></app-sidebar>
      <main class="app-main">
        <div class="mobile-header">
          <button class="mobile-menu-btn" (click)="sidebar.toggleSidebar()">
            <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
          </button>
          <h2>QA RAG Agent</h2>
        </div>
        <app-chat #chatRef (sessionCreated)="onSessionCreated()"></app-chat>
      </main>
    </div>
  `,
  styles: [`
    .app-layout {
      display: flex;
      height: 100dvh;
      width: 100vw;
      overflow: hidden;
      position: relative;
    }
    .app-main {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .mobile-header {
      display: none;
    }
    .mobile-overlay {
      display: none;
    }
    @media (max-width: 768px) {
      .mobile-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        background: #0c1222;
        border-bottom: 1px solid rgba(99, 102, 241, 0.1);
        z-index: 10;
        
        h2 {
          font-size: 1rem;
          font-weight: 600;
          margin: 0;
          color: #f1f5f9;
        }
      }
      .mobile-menu-btn {
        background: none;
        border: none;
        color: #94a3b8;
        cursor: pointer;
        padding: 0.25rem;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .mobile-overlay {
        display: block;
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 90; /* Just below sidebar's 100 */
      }
    }
  `],
})
export class AppComponent {
  @ViewChild('chatRef') chatRef!: ChatComponent;
  @ViewChild('sidebar') sidebarRef!: SidebarComponent;

  isMobile(): boolean {
    return window.innerWidth <= 768;
  }

  closeSidebarOnMobile(sidebar: SidebarComponent): void {
    if (this.isMobile() && !sidebar.isCollapsed) {
      sidebar.toggleSidebar();
    }
  }

  onSessionSelected(sessionId: string): void {
    this.chatRef.loadSession(sessionId);
  }

  onSettingsChanged(settings: { rag: boolean; tools: boolean }): void {
    this.chatRef.updateSettings(settings.rag, settings.tools);
  }

  onNewChat(): void {
    this.chatRef.sessionId = undefined;
    this.chatRef.clearChat();
  }

  onModelChanged(model: string): void {
    this.chatRef.selectedModel = model;
  }

  onSessionCreated(): void {
    this.sidebarRef.loadSessions();
  }
}
