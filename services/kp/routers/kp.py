import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KPDocument
from app.security import decode_access_token


router = APIRouter(prefix="/api/kp", tags=["kp"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

MAX_PAYLOAD_BYTES = 8 * 1024 * 1024  # 8 МБ на документ (фото в base64)


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    payload = decode_access_token(token)
    user_id = payload.get("sub") if payload else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
    try:
        return int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")


class KPIn(BaseModel):
    title: str = Field(default="Коммерческое предложение", max_length=255)
    payload: dict = Field(default_factory=dict)


class KPBriefOut(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str


class KPOut(KPBriefOut):
    payload: dict


def _brief(doc: KPDocument) -> KPBriefOut:
    return KPBriefOut(
        id=doc.id,
        title=doc.title,
        created_at=doc.created_at.strftime("%d.%m.%Y %H:%M") if doc.created_at else "",
        updated_at=doc.updated_at.strftime("%d.%m.%Y %H:%M") if doc.updated_at else "",
    )


def _get_own_doc(doc_id: int, user_id: int, db: Session) -> KPDocument:
    doc = db.get(KPDocument, doc_id)
    if not doc or doc.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    return doc


@router.get("/documents", response_model=List[KPBriefOut])
def list_documents(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    rows = db.scalars(
        select(KPDocument).where(KPDocument.user_id == user_id).order_by(KPDocument.updated_at.desc())
    ).all()
    return [_brief(r) for r in rows]


@router.post("/documents", response_model=KPOut, status_code=status.HTTP_201_CREATED)
def create_document(payload: KPIn, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    raw = json.dumps(payload.payload, ensure_ascii=False)
    if len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Документ слишком большой (макс. 8 МБ)")
    doc = KPDocument(user_id=user_id, title=payload.title.strip() or "Коммерческое предложение", payload=raw)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return KPOut(**_brief(doc).model_dump(), payload=payload.payload)


@router.get("/documents/{doc_id}", response_model=KPOut)
def get_document(doc_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    doc = _get_own_doc(doc_id, user_id, db)
    return KPOut(**_brief(doc).model_dump(), payload=json.loads(doc.payload or "{}"))


@router.put("/documents/{doc_id}", response_model=KPOut)
def update_document(doc_id: int, payload: KPIn, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    doc = _get_own_doc(doc_id, user_id, db)
    raw = json.dumps(payload.payload, ensure_ascii=False)
    if len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Документ слишком большой (макс. 8 МБ)")
    doc.title = payload.title.strip() or doc.title
    doc.payload = raw
    db.commit()
    db.refresh(doc)
    return KPOut(**_brief(doc).model_dump(), payload=payload.payload)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    doc = _get_own_doc(doc_id, user_id, db)
    db.delete(doc)
    db.commit()
