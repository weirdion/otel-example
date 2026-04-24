"""
Order Service Lambda Handler.

Manages orders and demonstrates cross-service tracing.
Emits telemetry via the shared OTel layer.
"""

from typing import Optional
from uuid import UUID

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from mangum import Mangum
from opentelemetry import trace

# Import from shared OTel layer
from otel_common import (
    ActionAttributes,
    UserContext,
    flush_telemetry,
    get_tracer,
    init_telemetry,
    set_standard_attributes,
)

from backend.shared.models import Order, OrderItem
from backend.shared.schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    ErrorResponse,
    GetOrderResponse,
    HealthResponse,
)

# Initialize Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize OTel (cold start)
init_telemetry()
otel_tracer = get_tracer("order-service")

# In-memory store for demo (would be DynamoDB in production)
_orders_store: dict[UUID, Order] = {}

# FastAPI app
app = FastAPI(
    title="Order Service API",
    description="Manage customer orders",
    version="1.0.0",
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            detail=str(exc) if logger.log_level == "DEBUG" else None,
        ).model_dump(),
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(service="order-service")


@app.post(
    "/orders",
    response_model=CreateOrderResponse,
    status_code=201,
    tags=["Orders"],
    responses={400: {"model": ErrorResponse}},
)
@tracer.capture_method
async def create_order(
    request: CreateOrderRequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
    x_org_id: str = Header(..., alias="X-Org-Id"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
    http_request: Request = None,
) -> CreateOrderResponse:
    """
    Create a new order.

    Requires X-User-Id and X-Org-Id headers for context.
    """
    # Get client IP from API Gateway context
    client_ip = None
    if http_request and http_request.client:
        client_ip = http_request.client.host

    # Convert request items to domain model
    order_items = [
        OrderItem(
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
        for item in request.items
    ]

    # Create the order
    order = Order(
        user_id=x_user_id,
        org_id=x_org_id,
        items=order_items,
        notes=request.notes,
    )

    # Create OTel span with standard attributes
    with otel_tracer.start_as_current_span("create_order") as span:
        user_context = UserContext(
            user_id=x_user_id,
            org_id=x_org_id,
            session_id=x_session_id,
            client_ip=client_ip,
        )
        action_attrs = ActionAttributes(
            action_type="order.create",
            action_id=str(order.id),
        )
        set_standard_attributes(span, user_context, action_attrs)

        # Add order-specific attributes
        span.set_attribute("order.item_count", len(order.items))
        span.set_attribute("order.total_amount", order.total_amount)
        span.set_attribute("order.status", order.status.value)

        # Simulate processing sub-spans
        with otel_tracer.start_as_current_span("validate_inventory") as validate_span:
            validate_span.set_attribute("items_checked", len(order.items))
            # In real app: check inventory availability
            pass

        with otel_tracer.start_as_current_span("calculate_pricing") as pricing_span:
            pricing_span.set_attribute("subtotal", order.total_amount)
            # In real app: apply discounts, tax, etc.
            pass

        # Store the order
        _orders_store[order.id] = order

        # Record metrics
        metrics.add_metric(
            name="OrdersCreated",
            unit=MetricUnit.Count,
            value=1,
        )
        metrics.add_metric(
            name="OrderValue",
            unit=MetricUnit.Count,
            value=order.total_amount,
        )

        logger.info(
            "Order created",
            extra={
                "order_id": str(order.id),
                "user_id": x_user_id,
                "org_id": x_org_id,
                "item_count": len(order.items),
                "total_amount": order.total_amount,
            },
        )

        # Get trace ID for response
        span_context = span.get_span_context()
        trace_id = format(span_context.trace_id, "032x") if span_context.is_valid else None

    return CreateOrderResponse(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        created_at=order.created_at,
        trace_id=trace_id,
    )


@app.get(
    "/orders/{order_id}",
    response_model=GetOrderResponse,
    tags=["Orders"],
    responses={404: {"model": ErrorResponse}},
)
@tracer.capture_method
async def get_order(
    order_id: UUID,
    x_user_id: str = Header(..., alias="X-User-Id"),
    x_org_id: str = Header(..., alias="X-Org-Id"),
) -> GetOrderResponse:
    """
    Get an order by ID.

    Only returns orders belonging to the requesting user's org.
    """
    with otel_tracer.start_as_current_span("get_order") as span:
        span.set_attribute("order.id", str(order_id))

        order = _orders_store.get(order_id)

        if order is None:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Order not found"))
            raise HTTPException(status_code=404, detail="Order not found")

        # Authorization check: same org only
        if order.org_id != x_org_id:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Forbidden"))
            logger.warning(
                "Unauthorized order access attempt",
                extra={
                    "order_id": str(order_id),
                    "requesting_org": x_org_id,
                    "order_org": order.org_id,
                },
            )
            raise HTTPException(status_code=404, detail="Order not found")

        return GetOrderResponse(
            id=order.id,
            user_id=order.user_id,
            org_id=order.org_id,
            items=order.items,
            status=order.status,
            total_amount=order.total_amount,
            created_at=order.created_at,
            updated_at=order.updated_at,
            notes=order.notes,
        )


# Lambda handler with Mangum
_mangum_handler = Mangum(app, lifespan="off")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda entry point."""
    try:
        return _mangum_handler(event, context)
    finally:
        # Ensure telemetry is flushed before Lambda freezes
        flush_telemetry()
