import { Injectable, InjectionToken, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { delay, map } from 'rxjs';

import { environment } from './environment';
import { ChatMessage, Conversation } from './models';
import { IdentityService } from './identity.service';
import { SAMPLE_LISTINGS } from './listing.service';

/**
 * قرارداد ارتباط فرانت‌اند با سرویس چت — فاز ۲.
 * مطابق FastAPI: /api/v1/conversations
 */
export abstract class ChatApi {
  abstract listConversations(page?: number): Observable<Conversation[]>;
  abstract createConversation(title: string): Observable<Conversation>;
  abstract getMessages(conversationId: string): Observable<ChatMessage[]>;
  abstract sendMessage(conversationId: string, text: string): Observable<ChatMessage>;
  abstract deleteConversation(conversationId: string): Observable<void>;
}

export const CHAT_API = new InjectionToken<ChatApi>('CHAT_API');

export function provideChatApi() {
  return environment.useMockChatApi
    ? { provide: CHAT_API, useClass: MockChatApi }
    : { provide: CHAT_API, useClass: HttpChatApi };
}

/** پیاده‌سازی واقعی FastAPI */
@Injectable()
export class HttpChatApi extends ChatApi {
  private readonly http = inject(HttpClient);
  private readonly identity = inject(IdentityService);
  private readonly base = environment.apiBaseUrl;

  private get headers() {
    return this.identity.headers();
  }

  listConversations(page = 1): Observable<Conversation[]> {
    return this.http
      .get<any>(`${this.base}/conversations`, {
        headers: this.headers,
        params: { page: String(page), pageSize: '50' },
      })
      .pipe(map((res) => res?.items ?? []));
  }

  createConversation(title: string): Observable<Conversation> {
    return this.http.post<Conversation>(`${this.base}/conversations`, { title }, { headers: this.headers });
  }

  getMessages(conversationId: string): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[]>(`${this.base}/conversations/${conversationId}/messages`, {
      headers: this.headers,
    });
  }

  sendMessage(conversationId: string, text: string): Observable<ChatMessage> {
    return this.http
      .post<any>(
        `${this.base}/conversations/${conversationId}/messages`,
        { content: text },
        { headers: this.headers },
      )
      .pipe(map((res) => res?.assistantMessage as ChatMessage));
  }

  deleteConversation(conversationId: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/conversations/${conversationId}`, { headers: this.headers });
  }
}

function shortenTitle(t: string): string {
  const clean = t.replace(/\s+/g, ' ').trim();
  return clean.length > 34 ? clean.slice(0, 34) + '…' : clean;
}

/** پیاده‌سازی نمونه برای پیش‌نمایش رابط کاربری بدون بکاند */
@Injectable()
export class MockChatApi extends ChatApi {
  private read<T>(key: string, fallback: T): T {
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : fallback;
    } catch {
      return fallback;
    }
  }

  private write(key: string, value: unknown): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* حافظه در دسترس نیست؛ بی‌صدا رد می‌شود */
    }
  }

  private convKey = () => 'bbai:conversations';
  private msgKey = (id: string) => `bbai:messages:${id}`;

  listConversations(): Observable<Conversation[]> {
    const list = this.read<Conversation[]>(this.convKey(), []).slice()
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
    return of(list).pipe(delay(150));
  }

  createConversation(title: string): Observable<Conversation> {
    const now = new Date().toISOString();
    const conv: Conversation = { id: uid(), title: shortenTitle(title), createdAt: now, updatedAt: now };
    const all = this.read<Conversation[]>(this.convKey(), []);
    all.push(conv);
    this.write(this.convKey(), all);
    this.write(this.msgKey(conv.id), []);
    return of(conv).pipe(delay(120));
  }

  getMessages(conversationId: string): Observable<ChatMessage[]> {
    return of(this.read<ChatMessage[]>(this.msgKey(conversationId), [])).pipe(delay(120));
  }

  deleteConversation(conversationId: string): Observable<void> {
    const all = this.read<Conversation[]>(this.convKey(), []).filter(c => c.id !== conversationId);
    this.write(this.convKey(), all);
    try {
      localStorage.removeItem(this.msgKey(conversationId));
    } catch { /* ignore */ }
    return of(undefined as unknown as void).pipe(delay(120));
  }

  sendMessage(conversationId: string, text: string): Observable<ChatMessage> {
    const now = new Date().toISOString();
    const userMsg: ChatMessage = { id: uid(), role: 'user', content: text, createdAt: now };
    const msgs = this.read<ChatMessage[]>(this.msgKey(conversationId), []);
    msgs.push(userMsg);
    const reply = this.buildReply(text);
    msgs.push(reply);
    this.write(this.msgKey(conversationId), msgs);

    const convs = this.read<Conversation[]>(this.convKey(), []);
    const conv = convs.find(c => c.id === conversationId);
    if (conv) {
      conv.updatedAt = now;
      this.write(this.convKey(), convs);
    }
    return of(reply).pipe(delay(900));
  }

  private buildReply(text: string): ChatMessage {
    const t = text.trim();
    const base = { id: uid(), role: 'assistant' as const, createdAt: new Date().toISOString() };

    const productTalk = /(پوست|مو|کرم|سرم|ضدآفتاب|محصول|مراقبت|آرایشی|بهداشتی|شامپو|ماسک|جوش)/.test(t);
    const searchTalk = /(آگهی|سالن|خدمت|جستجو|پیدا|دنبال)/.test(t);

    if (productTalk) {
      return {
        ...base,
        content: 'این پرسش به حوزه مراقبت پوست و مو مربوط می‌شود. طبق منابع راهنمای BeautyBoss، انتخاب محصول به نوع پوست، حساسیت‌ها و شرایط فردی بستگی دارد و برای شروع معمولاً یک روال ساده (شوینده ملایم، مرطوب‌کننده مناسب و ضدآفتاب روزانه) توصیه می‌شود.\nاگر نوع پوست یا موی خود را بگویید، راهنمایی دقیق‌تری می‌دهم. این پاسخ جایگزین توصیه پزشکی نیست.',
        sources: [{ title: 'مقالات راهنمای BeautyBoss', url: 'https://beautyboss.ir' }],
      };
    }
    if (searchTalk) {
      return {
        ...base,
        content: 'بر اساس درخواست شما چند آگهی مرتبط از سایت پیدا کردم. اگر محدوده قیمت، محله یا دسته خاصی مدنظرتان است بگویید تا جستجو را دقیق‌تر تکرار کنم.',
        listings: SAMPLE_LISTINGS.map(l => ({ ...l })),
      };
    }
    return {
      ...base,
      content: 'من دستیار هوشمند BeautyBoss هستم و در این کارها می‌توانم کمک کنم:\n• جستجوی آگهی‌های خدمات زیبایی سایت\n• پاسخ به پرسش‌های مراقبت پوست و مو با ذکر منبع\nکافی است درخواستتان را بنویسید.',
    };
  }
}

function uid(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);
}
