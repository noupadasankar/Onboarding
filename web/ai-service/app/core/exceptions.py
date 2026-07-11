"""Global FastAPI exception handlers for consistent JSON error responses.

All errors share the same envelope shape so clients need only one error parser:
  { "success": false, "error": { "code": str, "message": str } }

Register via register_exception_handlers(app) in main.py.
"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

_log = get_logger()


def _error_body(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


async def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    _log.warning("request_validation_error", path=str(request.url), errors=exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body("VALIDATION_ERROR", "Request validation failed."),
    )


async def _handle_unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    _log.exception("unhandled_exception", path=str(request.url), exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("INTERNAL_ERROR", "An unexpected error occurred."),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unhandled_error)  # type: ignore[arg-type]
