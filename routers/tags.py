from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.deps import require_admin
from database import get_db
from models.tag import Tag
from schemas.post import TagCreate, TagOut

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    return db.query(Tag).order_by(Tag.name.asc()).all()


@router.post("/", response_model=TagOut, status_code=201)
def create_tag(
    data: TagCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    existing_tag = db.query(Tag).filter(Tag.name == data.name).first()
    if existing_tag:
        raise HTTPException(status_code=409, detail="Tag już istnieje")

    tag = Tag(name=data.name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=204)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag nie istnieje")

    db.delete(tag)
    db.commit()