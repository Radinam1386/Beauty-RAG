class LLMError(Exception):
    """پایه همه خطاهای مدل زبانی."""

    retryable: bool = False


class LLMTimeoutError(LLMError):
    retryable = True


class LLMConnectionError(LLMError):
    """اتصال برقرار نشد (شبکه، DNS، proxy)."""

    retryable = True


class LLMServerError(LLMError):
    """خطای 5xx از سمت ارائه‌دهنده."""

    retryable = True


class LLMRateLimitError(LLMError):
    """خطای 429: تعداد درخواست یا سهمیه زیاد است."""

    retryable = True

    def __init__(self, message: str = "rate limited", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after  # ثانیه، اگر سرور اعلام کرده باشد


class LLMAuthError(LLMError):
    """کلید API اشتباه یا بدون دسترسی (401/403). تلاش دوباره فایده ندارد."""


class LLMBadResponseError(LLMError):
    """پاسخ خراب، ناقص یا خطای 4xx دیگر. تلاش دوباره فایده ندارد."""