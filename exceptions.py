from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    status:  int
    error:   str
    detail:  str | list | None = None
    path:    str | None = None

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                status=exc.status_code,
                error=exc.detail if isinstance(exc.detail, str) else "HTTP Error",
                path=str(request.url),
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = [
            {"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                status=422,
                error="Błąd walidacji danych",
                detail=errors,
                path=str(request.url),
            ).model_dump(),
        )