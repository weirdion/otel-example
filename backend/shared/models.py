"""
Domain models for the OTel demo.

These models represent the core business entities.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserAction(BaseModel):
    """Represents a tracked user action for audit purposes."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str
    org_id: str
    action_type: str = Field(
        ...,
        pattern=r"^[a-z]+\.[a-z_]+$",
        description="Action type in format 'domain.action'",
    )
    metadata: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_ip: Optional[str] = None
    session_id: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "user-123",
                    "org_id": "org-456",
                    "action_type": "order.view",
                    "metadata": {"order_id": "order-789"},
                    "timestamp": "2026-04-23T10:30:00Z",
                    "client_ip": "192.168.1.1",
                    "session_id": "sess-abc",
                }
            ]
        }
    }


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    """An item within an order."""

    product_id: str
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)

    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price


class Order(BaseModel):
    """Represents a customer order."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str
    org_id: str
    items: list[OrderItem] = Field(min_length=1)
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None

    @property
    def total_amount(self) -> float:
        return sum(item.total_price for item in self.items)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "user_id": "user-123",
                    "org_id": "org-456",
                    "items": [
                        {
                            "product_id": "prod-001",
                            "product_name": "Widget",
                            "quantity": 2,
                            "unit_price": 19.99,
                        }
                    ],
                    "status": "pending",
                    "created_at": "2026-04-23T10:30:00Z",
                    "updated_at": "2026-04-23T10:30:00Z",
                }
            ]
        }
    }
