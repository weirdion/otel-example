"""
API request/response schemas.

Separate from domain models to allow independent evolution
of API contracts and internal models.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.shared.models import OrderItem, OrderStatus


# =============================================================================
# Common Schemas
# =============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    service: str
    version: str = "1.0.0"


# =============================================================================
# User Actions Schemas
# =============================================================================


class CreateActionRequest(BaseModel):
    """Request to create a user action."""

    action_type: str = Field(
        ...,
        pattern=r"^[a-z]+\.[a-z_]+$",
        description="Action type in format 'domain.action'",
        examples=["order.view", "user.login", "product.search"],
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional context for the action",
    )


class CreateActionResponse(BaseModel):
    """Response after creating a user action."""

    id: UUID
    action_type: str
    timestamp: datetime
    trace_id: Optional[str] = Field(
        None,
        description="OpenTelemetry trace ID for correlation",
    )


class GetActionResponse(BaseModel):
    """Response for retrieving a user action."""

    id: UUID
    user_id: str
    org_id: str
    action_type: str
    metadata: dict[str, str]
    timestamp: datetime
    session_id: Optional[str] = None


# =============================================================================
# Order Schemas
# =============================================================================


class CreateOrderItemRequest(BaseModel):
    """Item in an order creation request."""

    product_id: str
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)


class CreateOrderRequest(BaseModel):
    """Request to create an order."""

    items: list[CreateOrderItemRequest] = Field(min_length=1)
    notes: Optional[str] = None


class CreateOrderResponse(BaseModel):
    """Response after creating an order."""

    id: UUID
    status: OrderStatus
    total_amount: float
    created_at: datetime
    trace_id: Optional[str] = Field(
        None,
        description="OpenTelemetry trace ID for correlation",
    )


class GetOrderResponse(BaseModel):
    """Response for retrieving an order."""

    id: UUID
    user_id: str
    org_id: str
    items: list[OrderItem]
    status: OrderStatus
    total_amount: float
    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None
