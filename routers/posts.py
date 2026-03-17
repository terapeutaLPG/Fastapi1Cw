from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.post import Post
from models.tag import Tag
from schemas.post import PostCreate, PostOut
from auth.deps import get_current_user, require_user
from models.user import User

router = APIRouter(prefix="/posts", tags=["posts"])

@router.get("/", response_model=list[PostOut])
def list_posts(
    db:        Session  = Depends(get_db),
    published: bool | None = Query(None),
    search:    str  | None = Query(None),
    page:      int         = Query(1, ge=1),
    per_page:  int         = Query(20, ge=1, le=100),
):
    query = db.query(Post)
    if published is not None:
        query = query.filter(Post.published == published)
    if search:
        pattern = f"%{search}%"
        query = query.filter(Post.title.ilike(pattern) | Post.content.ilike(pattern))
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items

@router.post("/", response_model=PostOut, status_code=201)
def create_post(
    data:         PostCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_user),
):
    tags = []
    if data.tag_ids:
        unique_tag_ids = list(dict.fromkeys(data.tag_ids))
        tags = db.query(Tag).filter(Tag.id.in_(unique_tag_ids)).all()
        if len(tags) != len(unique_tag_ids):
            raise HTTPException(status_code=404, detail="Jeden lub więcej tagów nie istnieje")

    post = Post(
        title=data.title,
        content=data.content,
        published=data.published,
        author_id=current_user.id,
    )
    post.tags = tags

    db.add(post)
    db.commit()
    db.refresh(post)
    return post

@router.delete("/{post_id}", status_code=204)
def delete_post(
    post_id:      int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Nie znaleziono postu")
    if current_user.role != "admin" and post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    db.delete(post)
    db.commit()