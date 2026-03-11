import { Component, ViewChild } from '@angular/core';
import { SidebarComponent } from './features/sidebar/sidebar.component';
import { ChatComponent } from './features/chat/chat.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [SidebarComponent, ChatComponent],
  template: `
    <div class="app-layout">
      <app-sidebar
        (sessionSelected)="onSessionSelected($event)"
        (settingsChanged)="onSettingsChanged($event)"
        (modelChanged)="onModelChanged($event)"
        (newChat)="onNewChat()"
      ></app-sidebar>
      <main class="app-main">
        <app-chat #chatRef (sessionCreated)="onSessionCreated()"></app-chat>
      </main>
    </div>
  `,
  styles: [`
    .app-layout {
      display: flex;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
    }
    .app-main {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
  `],
})
export class AppComponent {
  @ViewChild('chatRef') chatRef!: ChatComponent;
  @ViewChild(SidebarComponent) sidebarRef!: SidebarComponent;

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
