import { Component, inject, signal } from '@angular/core';

import { LISTINGS_API } from '../../core/listing.service';
import { ListingCategory, ListingSummary } from '../../core/models';
import { ListingCard } from '../../shared/listing-card';

@Component({
  selector: 'bb-search-page',
  imports: [ListingCard],
  templateUrl: './search-page.html',
  styleUrl: './search-page.scss',
})
export class SearchPage {
  private readonly listingsApi = inject(LISTINGS_API);

  protected readonly categories = signal<ListingCategory[]>([]);
  protected readonly query = signal('');
  protected readonly categoryId = signal('');
  protected readonly results = signal<ListingSummary[]>([]);
  protected readonly searching = signal(false);
  protected readonly searched = signal(false);
  protected readonly searchError = signal(false);
  protected readonly lastQuery = signal('');

  protected readonly examples = [
    'رنگ و مش مو در سعادت‌آباد',
    'میکاپ عروس با قیمت مناسب',
    'کاشت ناخن در کرج',
  ];

  constructor() {
    this.listingsApi.getCategories().subscribe(c => this.categories.set(c));
  }

  protected onQueryInput(ev: Event): void {
    this.query.set((ev.target as HTMLInputElement).value);
  }

  protected onCategoryChange(ev: Event): void {
    this.categoryId.set((ev.target as HTMLSelectElement).value);
  }

  protected useExample(q: string): void {
    if (this.searching()) return;
    this.query.set(q);
    this.search();
  }

  protected search(ev?: Event): void {
    ev?.preventDefault();
    const q = this.query().trim();
    if (!q || this.searching()) return;
    this.searching.set(true);
    this.searchError.set(false);
    this.listingsApi.search(q, this.categoryId() || null).subscribe({
      next: r => {
        this.results.set(r);
        this.lastQuery.set(q);
        this.searched.set(true);
        this.searching.set(false);
      },
      error: () => {
        this.searched.set(true);
        this.searchError.set(true);
        this.searching.set(false);
      },
    });
  }
}
