/**
 * تنظیمات اتصال فرانتاند به بکاند
 *
 * چت: FastAPI واقعی روی http://localhost:8000/api/v1
 * آگهیها: تا فاز ۳ (اتصال به Spring Boot) روی Mock میماند
 */
export const environment = {
  production: false,
  /** آدرس پایه سرویس هوش مصنوعی (FastAPI) */
  apiBaseUrl: 'http://localhost:8000/api/v1',
  /** چت واقعی */
  useMockChatApi: false,
  /** آگهیها هنوز Mock — فاز ۳ */
  useMockListingsApi: false,
  /** سازگاری با کد قبلی */
  useMockApi: false,
};
