"""
User Actions Lambda Handler.

Tracks user actions for security and audit purposes.
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

from backend.shared.models import UserAction
from backend.shared.schemas import (
    CreateActionRequest,
    CreateActionResponse,
    ErrorResponse,
    GetActionResponse,
    HealthResponse,
)

# Initialize Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize OTel (cold start)
init_telemetry()
otel_tracer = get_tracer("user-actions")

# In-memory store for demo (would be DynamoDB in production)
_actions_store: dict[UUID, UserAction] = {}

# FastAPI app
app = FastAPI(
    title="User Actions API",
    description="Track user actions for security and audit",
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
    return HealthResponse(service="user-actions")


@app.post(
    "/actions",
    response_model=CreateActionResponse,
    status_code=201,
    tags=["Actions"],
    responses={400: {"model": ErrorResponse}},
)
@tracer.capture_method
async def create_action(
    request: CreateActionRequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
    x_org_id: str = Header(..., alias="X-Org-Id"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
    http_request: Request = None,
) -> CreateActionResponse:
    """
    Create a new user action for audit tracking.

    Requires X-User-Id and X-Org-Id headers for context.
    """
    # Get client IP from API Gateway context
    client_ip = None
    if http_request and http_request.client:
        client_ip = http_request.client.host

    # Create the action
    action = UserAction(
        user_id=x_user_id,
        org_id=x_org_id,
        action_type=request.action_type,
        metadata=request.metadata,
        session_id=x_session_id,
        client_ip=client_ip,
    )

    # Create OTel span with standard attributes
    with otel_tracer.start_as_current_span("create_action") as span:
        user_context = UserContext(
            user_id=x_user_id,
            org_id=x_org_id,
            session_id=x_session_id,
            client_ip=client_ip,
        )
        action_attrs = ActionAttributes(
            action_type=request.action_type,
            action_id=str(action.id),
        )
        set_standard_attributes(span, user_context, action_attrs)

        # Add custom attributes
        span.set_attribute("action.metadata_keys", list(request.metadata.keys()))

        # Store the action
        _actions_store[action.id] = action

        # Record metric
        metrics.add_metric(
            name="ActionsCreated",
            unit=MetricUnit.Count,
            value=1,
        )
        metrics.add_dimension(name="ActionType", value=request.action_type)

        logger.info(
            "Action created",
            extra={
                "action_id": str(action.id),
                "action_type": request.action_type,
                "user_id": x_user_id,
                "org_id": x_org_id,
            },
        )

        # Get trace ID for response
        span_context = span.get_span_context()
        trace_id = format(span_context.trace_id, "032x") if span_context.is_valid else None

    return CreateActionResponse(
        id=action.id,
        action_type=action.action_type,
        timestamp=action.timestamp,
        trace_id=trace_id,
    )


@app.get(
    "/actions/{action_id}",
    response_model=GetActionResponse,
    tags=["Actions"],
    responses={404: {"model": ErrorResponse}},
)
@tracer.capture_method
async def get_action(
    action_id: UUID,
    x_user_id: str = Header(..., alias="X-User-Id"),
    x_org_id: str = Header(..., alias="X-Org-Id"),
) -> GetActionResponse:
    """
    Get a user action by ID.

    Only returns actions belonging to the requesting user's org.
    """
    with otel_tracer.start_as_current_span("get_action") as span:
        span.set_attribute("action.id", str(action_id))

        action = _actions_store.get(action_id)

        if action is None:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Action not found"))
            raise HTTPException(status_code=404, detail="Action not found")

        # Authorization check: same org only
        if action.org_id != x_org_id:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Forbidden"))
            logger.warning(
                "Unauthorized action access attempt",
                extra={
                    "action_id": str(action_id),
                    "requesting_org": x_org_id,
                    "action_org": action.org_id,
                },
            )
            raise HTTPException(status_code=404, detail="Action not found")

        return GetActionResponse(
            id=action.id,
            user_id=action.user_id,
            org_id=action.org_id,
            action_type=action.action_type,
            metadata=action.metadata,
            timestamp=action.timestamp,
            session_id=action.session_id,
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
