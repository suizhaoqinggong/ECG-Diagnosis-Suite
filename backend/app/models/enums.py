from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageType(str, Enum):
    INTRO = "intro"
    PROMPT = "prompt"
    GUIDANCE = "guidance"
    DIAGNOSIS = "diagnosis"


class MessageStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    ERROR = "error"
