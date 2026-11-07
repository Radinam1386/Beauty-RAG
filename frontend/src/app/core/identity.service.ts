import { Injectable } from '@angular/core';

/**
 * شناسه نشست مهمان / کاربر برای هدرهای Chat API.
 * کاربر لاگین‌شده: سایت اصلی باید X-User-Id را ست کند (یا این سرویس از localStorage بخواند).
 * مهمان: شناسه در localStorage نگه داشته می‌شود.
 */
@Injectable({ providedIn: 'root' })
export class IdentityService {
  private readonly guestKey = 'bbai:guest-session';
  private readonly userKey = 'bbai:user-id';

  guestSessionId(): string {
    try {
      let id = localStorage.getItem(this.guestKey);
      if (!id) {
        id = uid();
        localStorage.setItem(this.guestKey, id);
      }
      return id;
    } catch {
      return uid();
    }
  }

  /** شناسه کاربر لاگین‌شده اگر سایت اصلی گذاشته باشد. */
  externalUserId(): string | null {
    try {
      return localStorage.getItem(this.userKey);
    } catch {
      return null;
    }
  }

  setExternalUserId(id: string | null): void {
    try {
      if (id) localStorage.setItem(this.userKey, id);
      else localStorage.removeItem(this.userKey);
    } catch { /* ignore */ }
  }

  headers(): Record<string, string> {
    const userId = this.externalUserId();
    if (userId) return { 'X-User-Id': userId };
    return { 'X-Guest-Session-Id': this.guestSessionId() };
  }
}

function uid(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);
}
