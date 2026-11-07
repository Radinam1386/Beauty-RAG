class ChatError(Exception):
    """پایه خطاهای چت."""


class ConversationNotFound(ChatError):
    """گفتگوی موردنظر پیدا نشد."""


class ConversationAccessError(ChatError):
    """گفتگو وجود دارد ولی متعلق به این کاربر/مهمان نیست."""


class EmptyMessageError(ChatError):
    """متن پیام خالی است."""


class MessageTooLongError(ChatError):
    """متن پیام بیش از حد مجاز است."""
