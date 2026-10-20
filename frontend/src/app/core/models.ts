/** مدل‌های داده مشترک فرانت‌اند — قرارداد این مدل‌ها باید با قرارداد API سند پروژه هم‌راستا بماند. */

export function uid(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string; // ISO
  updatedAt: string; // ISO
}

/** منبعی که پاسخ تخصصی دستیار به آن ارجاع می‌دهد (خروجی RAG) */
export interface SourceRef {
  title: string;
  url?: string;
}

/** خلاصه آگهی — معادل خروجی ابزار search_listings در سند پروژه */
export interface ListingSummary {
  id: string;
  title: string;
  categoryId: string;
  categoryName: string;
  city: string;
  area?: string;
  priceLabel?: string;
  providerName?: string;
  url?: string;
  /** فقط در داده نمونه (Mock) مقدار دارد و در رابط به‌صورت برچسب «نمونه» دیده می‌شود. */
  isSample?: boolean;
}

export interface ListingCategory {
  id: string;
  name: string;
}

export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  /** آگهی‌های پیوست پاسخ (حاصل Tool Calling) */
  listings?: ListingSummary[];
  /** منابع پاسخ‌های تخصصی (RAG) */
  sources?: SourceRef[];
  /** پاسخی که به خطا خورده است */
  failed?: boolean;
}

/** پیش‌نویس درخواست ثبت آگهی — مطابق جریان چندمرحله‌ای فاز ۳ سند پروژه */
export interface ListingRequestDraft {
  categoryId: string | null;
  title: string;
  description: string;
  city: string;
  area: string;
  budgetLabel: string;
  contactPhone: string;
}

export interface ListingRequestResult {
  id: string;
  status: 'submitted' | 'review';
  message: string;
}
