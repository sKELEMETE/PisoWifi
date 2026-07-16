import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        request: Request,
        exc: ValidationError
    ):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Validation failed",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def fastapi_validation_handler(
        request: Request,
        exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Request validation failed",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception
    ):
        logger.exception("Unhandled server exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error. Please check backend logs or contact the administrator.",
                "errors": [],
            },
        )
