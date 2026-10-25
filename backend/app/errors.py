"""Centralised error handling: every error leaves the API in the same JSON shape."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status_code, message, fields=None):
        self.status_code = status_code
        self.message = message
        self.fields = fields or {}


def _body(message, fields=None):
    return {"error": {"message": message, "fields": fields or {}}}


def register_error_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.message, exc.fields))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        fields = {}
        for err in exc.errors():
            loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
            name = loc[-1] if loc else "request"
            message = err["msg"].replace("Value error, ", "")
            fields.setdefault(name, message)
        return JSONResponse(status_code=422, content=_body("Validation failed", fields))

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content=_body(str(exc.detail)))
