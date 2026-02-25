from typing import Any, Optional
from fastapi.responses import JSONResponse


def success_response(data: Any = None, message: str = "Operation successful", status_code: int = 200) -> JSONResponse:
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    return JSONResponse(content=body, status_code=status_code)


def error_response(
    code: str,
    message: str,
    status_code: int = 400,
    details: Optional[list] = None,
) -> JSONResponse:
    error: dict = {"code": code, "message": message}
    if details:
        error["details"] = details
    return JSONResponse(content={"success": False, "error": error}, status_code=status_code)


def paginated_response(items: list, page: int, limit: int, total: int) -> dict:
    total_pages = (total + limit - 1) // limit
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": total_pages,
            "hasNext": page < total_pages,
            "hasPrev": page > 1,
        },
    }
