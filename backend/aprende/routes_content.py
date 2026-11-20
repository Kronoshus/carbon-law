
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from . import content

router = APIRouter()

def _staff(authorization):
    if not authorization:
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})
    import app as backend_app
    u, _ = backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    return u

def _map(e):
    msg = str(e)
    if isinstance(e, content.InvalidError):
        return 422, {"error": "invalid", "errors": e.errors}
    if isinstance(e, content.LanguageError):
        return 422, {"error": "languages", "missing": e.missing}
    if isinstance(e, content.PlaceholderError):
        return 422, {"error": "placeholders", "missing": e.missing}
    if isinstance(e, content.NoDraftError) or isinstance(e, content.NoVersionError):
        return 409, {"error": "no_draft"}
    if isinstance(e, PermissionError):
        return 403, {"error": str(e)}
    if isinstance(e, KeyError):
        return 404, {"error": str(e)}
    if isinstance(e, content.ShapeError):
        return 422, {"error": "bad_shape"}
    return 400, {"error": msg}

@router.get("/staff/content")
def list_entries(kind: str = "item", authorization: str | None = Header(default=None)):
    _staff(authorization)
    try:
        return {"entries": content.entries(kind)}
    except Exception as e:
        st, body = _map(e)
        return JSONResponse(status_code=st, content=body)

@router.get("/staff/content/{entry_id:path}/preview")
def preview(entry_id: str, version: int = 0, lang: str = "es", authorization: str | None = Header(default=None)):
    _staff(authorization)
    try:
        return content.preview(entry_id, version, lang)
    except Exception as e:
        st, body = _map(e)
        return JSONResponse(status_code=st, content=body)

@router.get("/staff/content/{entry_id:path}")
def get_entry(entry_id: str, authorization: str | None = Header(default=None)):
    _staff(authorization)
    try:
        return content.entry(entry_id)
    except Exception as e:
        st, body = _map(e)
        return JSONResponse(status_code=st, content=body)

@router.put("/staff/content/{entry_id:path}/draft")
def save_draft(entry_id: str, payload: dict, authorization: str | None = Header(default=None)):
    u = _staff(authorization)
    try:
        return content.save_draft(entry_id, payload.get("body"), u["email"])
    except Exception as e:
        st, body = _map(e)
        return JSONResponse(status_code=st, content=body)

@router.post("/staff/content/{entry_id:path}/submit")
def submit(entry_id: str, authorization: str | None = Header(default=None)):
    u = _staff(authorization)
    try:
        return content.submit(entry_id, u["email"])
    except Exception as e:
        st, body = _map(e)
        return JSONResponse(status_code=st, content=body)

@router.post("/staff/content/{entry_id:path}/approve")
def approve(entry_id: str, payload: dict, authorization: str | None = Header(default=None)):
    u = _staff(authorization)
    if u["role"] != "attorney":
        return JSONResponse(status_code=403, content={"error": "attorney_only"})
    try:
        return content.approve_version(entry_id, payload.get("version"), u["email"])
    except Exception as e:
        st, body = _map(e)
        return JSONResponse(status_code=st, content=body)

@router.post("/staff/content/{entry_id:path}/publish")
def publish(entry_id: str, payload: dict, authorization: str | None = Header(default=None)):
    u = _staff(authorization)
    try:
        return content.publish_version(entry_id, payload.get("version"), u["email"])
    except Exception as e:
        st, body = _map(e)
        return JSONResponse(status_code=st, content=body)

