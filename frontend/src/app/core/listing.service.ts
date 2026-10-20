import { Injectable, InjectionToken, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs';

import { environment } from './environment';
import { ListingCategory, ListingRequestDraft, ListingRequestResult, ListingSummary, uid } from './models';

/**
 * قرارداد سرویس آگهی — معادل ابزارهای سند پروژه:
 * get_listing_categories / search_listings و جریان ثبت درخواست آگهی.
 */
export abstract class ListingsApi {
  abstract getCategories(): Observable<ListingCategory[]>;
  abstract search(query: string, categoryId?: string | null): Observable<ListingSummary[]>;
  abstract submitRequest(draft: ListingRequestDraft): Observable<ListingRequestResult>;
}

export const LISTINGS_API = new InjectionToken<ListingsApi>('LISTINGS_API');

export function provideListingsApi() {
  return environment.useMockApi
    ? { provide: LISTINGS_API, useClass: MockListingsApi }
    : { provide: LISTINGS_API, useClass: HttpListingsApi };
}

/** پیاده‌سازی واقعی — نقاط اتصال به سرویس AI و APIهای Spring Boot */
@Injectable()
export class HttpListingsApi extends ListingsApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  getCategories(): Observable<ListingCategory[]> {
    return this.http.get<ListingCategory[]>(`${this.base}/listings/categories`);
  }

  search(query: string, categoryId?: string | null): Observable<ListingSummary[]> {
    return this.http.post<ListingSummary[]>(`${this.base}/listings/search`, {
      query,
      categoryId: categoryId ?? null,
    });
  }

  submitRequest(draft: ListingRequestDraft): Observable<ListingRequestResult> {
    // ثبت نهایی از مسیر Spring Boot انجام می‌شود و داده‌ها مجدداً اعتبارسنجی می‌شوند.
    return this.http.post<ListingRequestResult>(`${this.base}/listing-requests`, draft);
  }
}

/** داده نمونه — فقط در حالت Mock استفاده می‌شود و در رابط با برچسب «نمونه» مشخص است. */
export const SAMPLE_CATEGORIES: ListingCategory[] = [
  { id: 'hair', name: 'کوتاهی و رنگ مو' },
  { id: 'makeup', name: 'میکاپ و گریم' },
  { id: 'nail', name: 'ناخن' },
  { id: 'skin', name: 'پوست و لیفت' },
  { id: 'lash', name: 'مژه و ابرو' },
];

export const SAMPLE_LISTINGS: ListingSummary[] = [
  {
    id: 'sample-1',
    title: 'رنگ و مش مو با مواد ارگانیک',
    categoryId: 'hair',
    categoryName: 'کوتاهی و رنگ مو',
    city: 'تهران',
    area: 'سعادت‌آباد',
    priceLabel: 'از ۹۵۰٬۰۰۰ تومان',
    providerName: 'سالن آرتمیس',
    url: 'https://beautyboss.ir',
    isSample: true,
  },
  {
    id: 'sample-2',
    title: 'میکاپ عروس حرفه‌ای به‌همراه تست میکاپ',
    categoryId: 'makeup',
    categoryName: 'میکاپ و گریم',
    city: 'تهران',
    area: 'ولنجک',
    priceLabel: 'توافقی',
    providerName: 'آتلیه نیکا',
    url: 'https://beautyboss.ir',
    isSample: true,
  },
  {
    id: 'sample-3',
    title: 'کاشت ناخن پودر و ژلیش',
    categoryId: 'nail',
    categoryName: 'ناخن',
    city: 'کرج',
    area: 'عظیمیه',
    priceLabel: 'از ۴۸۰٬۰۰۰ تومان',
    providerName: 'استودیو رها',
    url: 'https://beautyboss.ir',
    isSample: true,
  },
];

/** پیاده‌سازی نمونه برای پیش‌نمایش رابط کاربری بدون بکاند */
@Injectable()
export class MockListingsApi extends ListingsApi {
  getCategories(): Observable<ListingCategory[]> {
    return of(SAMPLE_CATEGORIES.map(c => ({ ...c }))).pipe(delay(120));
  }

  search(query: string, categoryId?: string | null): Observable<ListingSummary[]> {
    let list = SAMPLE_LISTINGS.slice();
    if (categoryId) {
      list = list.filter(l => l.categoryId === categoryId);
    }
    const q = query.trim();
    if (q) {
      // جستجوی واژه‌ای ساده؛ در نسخه واقعی، جستجوی معنایی سمت سرویس AI انجام می‌شود.
      const tokens = q.split(/[\s،,]+/).filter(t => t.length > 1);
      list = list.filter(l => {
        const haystack = [l.title, l.city, l.area ?? '', l.categoryName, l.providerName ?? ''].join(' ');
        return tokens.some(t => haystack.includes(t));
      });
    }
    return of(list.map(l => ({ ...l }))).pipe(delay(700));
  }

  submitRequest(draft: ListingRequestDraft): Observable<ListingRequestResult> {
    return of({
      id: uid(),
      status: 'submitted' as const,
      message: 'درخواست آگهی شما ثبت شد. کارشناسان BeautyBoss پس از بررسی اطلاعات، نتیجه را اطلاع می‌دهند.',
    }).pipe(delay(900));
  }
}
