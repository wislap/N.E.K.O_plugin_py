import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_MAX_LENGTH = 128

logger = logging.getLogger("app.request")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


def create_request_id() -> str:
    return f"req-{uuid.uuid4().hex}"


def normalize_request_id(value: str | None) -> str | None:
    if value is None:
        return None

    request_id = value.strip()
    if not request_id or len(request_id) > REQUEST_ID_MAX_LENGTH:
        return None
    if not _REQUEST_ID_PATTERN.fullmatch(request_id):
        return None
    return request_id


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER)) or create_request_id()
    request.state.request_id = request_id
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers[REQUEST_ID_HEADER] = request_id
    logger.info(
        "request_completed request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response
