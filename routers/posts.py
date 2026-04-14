from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth.deps import get_current_user, require_admin, require_user
from database import get_db
from models.post import Post
from models.tag import Tag
from models.user import User
from schemas.post import PostCreate, PostListResponse, PostOut, PostUpdate

router = APIRouter(prefix="/posts", tags=["posts"])


def _resolve_tags(tag_ids: list[int] | None, db: Session) -> list[Tag]:
    if not tag_ids:
        return []

    unique_tag_ids = list(dict.fromkeys(tag_ids))
    tags = db.query(Tag).filter(Tag.id.in_(unique_tag_ids)).all()
    if len(tags) != len(unique_tag_ids):
        raise HTTPException(status_code=404, detail="Jeden lub więcej tagów nie istnieje")
    return tags


@router.get("/", response_model=PostListResponse)
def list_posts(
    db: Session = Depends(get_db),
    published: bool | None = Query(None),
    author_id: int | None = Query(None),
    tag: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    query = db.query(Post)
    if published is not None:
        query = query.filter(Post.published == published)
    if author_id is not None:
        query = query.filter(Post.author_id == author_id)
    if tag:
        query = query.join(Post.tags).filter(Tag.name.ilike(tag)).distinct()
    if search:
        pattern = f"%{search}%"
        query = query.filter(Post.title.ilike(pattern) | Post.content.ilike(pattern))

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if total else 0,
        "items": items,
    }


@router.get("/admin/all", response_model=list[PostOut], dependencies=[Depends(require_admin)])
def admin_list_all_posts(db: Session = Depends(get_db)):
    return db.query(Post).order_by(Post.id.desc()).all()


@router.get("/{post_id}", response_model=PostOut)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Nie znaleziono postu")
    return post


@router.post("/", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    data: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    post = Post(
        title=data.title,
        content=data.content,
        published=data.published,
        author_id=current_user.id,
    )
    post.tags = _resolve_tags(data.tag_ids, db)

    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.patch("/{post_id}", response_model=PostOut)
def update_post(
    post_id: int,
    data: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Nie znaleziono postu")

    if current_user.role != "admin" and post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Brak uprawnień")

    payload = data.model_dump(exclude_none=True)
    if "tag_ids" in payload:
        post.tags = _resolve_tags(payload.pop("tag_ids"), db)

    for field, value in payload.items():
        setattr(post, field, value)

    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Nie znaleziono postu")
    if current_user.role != "admin" and post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Brak uprawnień")

    db.delete(post)
    db.commit()
