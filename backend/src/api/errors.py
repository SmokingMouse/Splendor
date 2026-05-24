from __future__ import annotations

from fastapi import HTTPException


class DomainError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def domain_error(code: str, message: str, status_code: int = 400) -> DomainError:
    return DomainError(code, message, status_code)


def as_http_exception(exc: DomainError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


def bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)
