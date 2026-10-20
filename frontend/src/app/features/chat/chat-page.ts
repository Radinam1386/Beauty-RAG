import { Component, ElementRef, effect, inject, signal, viewChild } from '@angular/core';

import { CHAT_API } from '../../core/chat.service';
import { ChatMessage, Conversation, uid } from '../../core/models';
import { ListingCard } from '../../shared/listing-card';

@Component({
  selector: 'bb-chat-page',
  imports: [ListingCard],
  templateUrl: './chat-page.html',
  styleUrl: './chat-page.scss',
})
export class ChatPage {
  private readonly chatApi = inject(CHAT_API);

  protected readonly conversations = signal<Conversation[]>([]);
  protected readonly activeId = signal<string | null>(null);
  protected readonly messages = signal<ChatMessage[]>([]);
  protected readonly draft = signal('');
  protected readonly sending = signal(false);
  protected readonly loadingList = signal(true);
  protected readonly sidebarOpen = signal(false);
  protected readonly confirmDeleteId = signal<string | null>(null);

  private readonly composerEl = viewChild<ElementRef<HTMLTextAreaElement>>('composerEl');
  private readonly bottomAnchor = viewChild<ElementRef<HTMLElement>>('bottomAnchor');

  protected readonly suggestions = [
    { label: 'رنگ و مش مو در تهران', text: 'دنبال رنگ و مش مو در تهران هستم، چند آگهی مناسب پیدا کن.' },
    { label: 'کرم مرطوب‌کننده برای پوست خشک', text: 'برای پوست خشک چه کرم مرطوب‌کننده‌ای مناسب است؟' },
    { label: 'آگهی میکاپ عروس در تهران', text: 'دنبال آگهی میکاپ عروس در تهران می‌گردم.' },
  ];

  constructor() {
    // اسکرول خودکار به آخرین پیام
    effect(() => {
      this.messages();
      this.sending();
      setTimeout(() => {
        this.bottomAnchor()?.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }, 50);
    });
  }

  protected loadConversations(): void {
    this.loadingList.set(true);
    this.chatApi.listConversations().subscribe(list => {
      this.conversations.set(list);
      this.loadingList.set(false);
    });
  }

  protected select(conv: Conversation): void {
    this.activeId.set(conv.id);
    this.sidebarOpen.set(false);
    this.chatApi.getMessages(conv.id).subscribe(msgs => this.messages.set(msgs));
  }

  protected newChat(): void {
    this.activeId.set(null);
    this.messages.set([]);
    this.sidebarOpen.set(false);
    setTimeout(() => this.composerEl()?.nativeElement.focus(), 0);
  }

  protected useSuggestion(s: { text: string }): void {
    if (this.sending()) return;
    this.draft.set(s.text);
    this.send();
  }

  protected onInput(ev: Event): void {
    const el = ev.target as HTMLTextAreaElement;
    this.draft.set(el.value);
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  protected onComposerKeydown(ev: KeyboardEvent): void {
    if (ev.key === 'Enter' && !ev.shiftKey) {
      ev.preventDefault();
      this.send();
    }
  }

  protected send(): void {
    const text = this.draft().trim();
    if (!text || this.sending()) return;
    this.draft.set('');
    const el = this.composerEl()?.nativeElement;
    if (el) el.style.height = 'auto';
    this.sending.set(true);

    const userMsg: ChatMessage = {
      id: uid(),
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    };

    const run = (convId: string) => {
      if (this.activeId() !== convId) this.activeId.set(convId);
      this.sidebarOpen.set(false);
      this.messages.update(list => [...list, userMsg]);
      this.chatApi.sendMessage(convId, text).subscribe({
        next: reply => {
          this.messages.update(list => [...list, reply]);
          this.sending.set(false);
        },
        error: () => {
          this.messages.update(list => [
            ...list,
            {
              id: uid(),
              role: 'assistant',
              failed: true,
              createdAt: new Date().toISOString(),
              content: 'ارتباط با سرویس هوش مصنوعی برقرار نشد. لطفاً چند لحظه بعد دوباره تلاش کنید.',
            },
          ]);
          this.sending.set(false);
        },
      });
    };

    const current = this.activeId();
    if (current) {
      run(current);
    } else {
      // گفتگوی تازه: با اولین پیام ساخته می‌شود تا فهرست، شلوغ از گفتگوهای خالی نشود.
      this.chatApi.createConversation(text).subscribe(c => {
        this.conversations.update(list => [c, ...list]);
        run(c.id);
      });
    }
  }

  protected askDelete(conv: Conversation): void {
    this.confirmDeleteId.set(conv.id);
  }

  protected cancelDelete(): void {
    this.confirmDeleteId.set(null);
  }

  protected remove(conv: Conversation): void {
    this.confirmDeleteId.set(null);
    this.chatApi.deleteConversation(conv.id).subscribe(() => {
      this.conversations.update(list => list.filter(c => c.id !== conv.id));
      if (this.activeId() === conv.id) {
        this.activeId.set(null);
        this.messages.set([]);
      }
    });
  }

  protected faDate(iso: string): string {
    try {
      return new Intl.DateTimeFormat('fa-IR', { month: 'long', day: 'numeric' }).format(new Date(iso));
    } catch {
      return '';
    }
  }
}
