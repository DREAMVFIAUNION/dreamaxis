from __future__ import annotations


def success_response(data, message: str | None = None):
    return {"success": True, "data": data, "message": message}


def paginated_response(data):
    return {"success": True, "data": data, "meta": {"total": len(data)}}
