"""
Standard attribute schemas for OTel spans.

Provides Pydantic models for validating and setting consistent
attributes across all Lambda functions.
"""

from datetime import datetime, timezone
from typing import Optional

from opentelemetry import trace
from pydantic import BaseModel, Field


class UserContext(BaseModel):
    """User context attributes for security and audit."""

    user_id: str = Field(..., min_length=1, description="Unique user identifier")
    org_id: str = Field(..., min_length=1, description="Organization identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    client_ip: Optional[str] = Field(None, description="Client IP address")

    def to_attributes(self) -> dict[str, str]:
        """Convert to OTel span attributes."""
        attrs = {
            "user.id": self.user_id,
            "org.id": self.org_id,
        }
        if self.session_id:
            attrs["session.id"] = self.session_id
        if self.client_ip:
            attrs["client.ip"] = self.client_ip
        return attrs


class ActionAttributes(BaseModel):
    """Action attributes for tracking user actions."""

    action_type: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-z]+\.[a-z_]+$",
        description="Action type in format 'domain.action' (e.g., 'order.create')",
    )
    action_id: Optional[str] = Field(None, description="Unique action/request ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Action timestamp in UTC",
    )

    def to_attributes(self) -> dict[str, str]:
        """Convert to OTel span attributes."""
        attrs = {
            "action.type": self.action_type,
            "action.timestamp": self.timestamp.isoformat(),
        }
        if self.action_id:
            attrs["action.id"] = self.action_id
        return attrs


def set_user_context(span: trace.Span, context: UserContext) -> None:
    """Set user context attributes on a span."""
    for key, value in context.to_attributes().items():
        span.set_attribute(key, value)


def set_action_attributes(span: trace.Span, action: ActionAttributes) -> None:
    """Set action attributes on a span."""
    for key, value in action.to_attributes().items():
        span.set_attribute(key, value)


def set_standard_attributes(
    span: trace.Span,
    user_context: UserContext,
    action: ActionAttributes,
) -> None:
    """Set all standard attributes on a span."""
    set_user_context(span, user_context)
    set_action_attributes(span, action)
