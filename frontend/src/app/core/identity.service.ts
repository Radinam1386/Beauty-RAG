import { Injectable } from '@angular/core';

import { environment } from './environment';

/**
 * هویت درخواست‌های چت.
 *
 * کاربر لاگین‌شده: توکن JWT که سایت اصلی در localStorage (کلید environment.authTokenKey)
 * می‌گذارد یا با setToken() به ما می‌دهد؛ آن را به‌صورت Authorization: Bearer می‌فرستیم.
 * مهمان: شناسه نشست در localStorage نگه داشته می‌شود.
 */
@Injectable({ providedIn: 'root' })
export class IdentityService {
  private readonly guestKey = 'bbai:guest-session';

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

  /** توکن JWT سایت اصلی؛ null یعنی مهمان. */
  token(): string | null {
    try {
      return localStorage.getItem(environment.authTokenKey);
    } catch {
      return null;
    }
  }

  /** سایت اصلی بعد از لاگین/رفرش توکن صدا می‌زند؛ خروج = null. */
  setToken(token: string | null): void {
    try {
      if (token) localStorage.setItem(environment.authTokenKey, token);
      else localStorage.removeItem(environment.authTokenKey);
    } catch { /* ignore */ }
  }

  isLoggedIn(): boolean {
    return !!this.token();
  }

  headers(): Record<string, string> {
    const token = this.token();
    if (token) return { Authorization: `Bearer ${token}` };
    return { 'X-Guest-Session-Id': this.guestSessionId() };
  }
}

function uid(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);
}
