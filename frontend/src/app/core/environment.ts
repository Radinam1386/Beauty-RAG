export const environment = {
  production: false,
  /**
   * آدرس پایه سرویس هوش مصنوعی (FastAPI)
   * بر اساس hostname مرورگر ساخته می‌شود تا دسترسی با IP محلی (LAN) هم کار کند:
   * اگر با http://192.168.x.x:4200 باز شود، API هم همان IP را صدا می‌زند.
   */
  apiBaseUrl: `http://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:8000/api/v1`,
  authTokenKey: 'bbai:access-token',
  useMockChatApi: false,
  useMockListingsApi: false,
  useMockApi: false,
};
