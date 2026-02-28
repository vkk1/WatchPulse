from fastapi import APIRouter, HTTPException, Query

from app.services.model_catalog import get_model_detail, list_models

router = APIRouter(prefix="/v1/models", tags=["models"])


@router.get("")
def get_models(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    q: str | None = Query(default=None),
    collection: str | None = Query(default=None),
    sort: str = Query(default="wait_time_index_desc"),
) -> dict:
    try:
        return list_models(page=page, page_size=page_size, q=q, collection=collection, sort=sort)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {exc}") from exc


@router.get("/{model_id}")
def get_model_by_id(model_id: int) -> dict:
    try:
        payload = get_model_detail(model_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch model detail: {exc}") from exc

    if payload is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return payload
