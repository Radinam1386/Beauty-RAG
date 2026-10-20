import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'chat' },
  {
    path: 'chat',
    title: 'گفتگو | دستیار هوشمند BeautyBoss',
    loadComponent: () => import('./features/chat/chat-page').then(m => m.ChatPage),
  },
  {
    path: 'search',
    title: 'جستجوی آگهی | دستیار هوشمند BeautyBoss',
    loadComponent: () => import('./features/search/search-page').then(m => m.SearchPage),
  },
  {
    path: 'guide',
    title: 'راهنما | دستیار هوشمند BeautyBoss',
    loadComponent: () => import('./features/guide/guide-page').then(m => m.GuidePage),
  },
  { path: '**', redirectTo: 'chat' },
];
