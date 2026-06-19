from enum import Enum


class OrderStatus(str, Enum):
    AWAITING_RECEIPT = "awaiting_receipt"
    PENDING = "pending"
    COMPLETED = "completed"
    REJECTED = "rejected"


class UserState(str, Enum):
    NONE = "none"
    AWAITING_BROADCAST = "awaiting_broadcast"
    AWAITING_PRICE_INPUT = "awaiting_price_input"
