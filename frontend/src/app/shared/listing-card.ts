import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { ListingSummary } from '../core/models';

/** کارت نمایش خلاصه آگهی — در گفتگو و صفحه جستجو استفاده می‌شود. */
@Component({
  selector: 'bb-listing-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <article class="listing-card">
      @if (listing().isSample) {
        <span class="chip chip-muted sample-chip">نمونه</span>
      }
      <h4 class="lc-title">{{ listing().title }}</h4>
      <div class="lc-meta">
        <span class="chip">{{ listing().categoryName }}</span>
        <span class="lc-loc">{{ listing().city }}@if (listing().area) { — {{ listing().area }}}</span>
      </div>
      <div class="lc-foot">
        @if (listing().priceLabel) {
          <span class="lc-price">{{ listing().priceLabel }}</span>
        }
        @if (listing().providerName) {
          <span class="lc-provider">{{ listing().providerName }}</span>
        }
      </div>
      @if (listing().url) {
        <a class="lc-link" [href]="listing().url" target="_blank" rel="noopener">مشاهده در BeautyBoss</a>
      }
    </article>
  `,
  styles: `
    .listing-card {
      position: relative;
      background: var(--bb-surface);
      border: 1px solid var(--bb-border);
      border-radius: var(--bb-radius);
      padding: .9rem 1rem;
      box-shadow: var(--bb-shadow);
      display: flex;
      flex-direction: column;
      gap: .45rem;
    }
    .lc-title {
      font-size: .95rem;
      font-weight: 700;
      color: var(--bb-deep);
      padding-inline-end: 2.6rem;
    }
    .lc-meta {
      display: flex;
      align-items: center;
      gap: .5rem;
      flex-wrap: wrap;
    }
    .lc-loc { font-size: .8rem; color: var(--bb-muted); }
    .lc-foot {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: .5rem;
      flex-wrap: wrap;
      margin-top: auto;
    }
    .lc-price {
      font-weight: 700;
      color: var(--bb-primary-strong);
      font-size: .88rem;
    }
    .lc-provider { font-size: .8rem; color: var(--bb-faint); }
    .lc-link { font-size: .82rem; font-weight: 600; }
    .sample-chip {
      position: absolute;
      top: .6rem;
      inset-inline-end: .6rem;
    }
  `,
})
export class ListingCard {
  readonly listing = input.required<ListingSummary>();
}
