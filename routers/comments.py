from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.comment import Comment
from models.post import Post
from schemas.comment import CommentCreate, CommentOut
from auth.deps import get_current_user, require_user
from models.user import User

router = APIRouter(tags=["comments"])

@router.get("/posts/{post_id}/comments", response_model=list[CommentOut])
def get_comments(post_id: int, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post nie istnieje")
    return post.comments

@router.post("/posts/{post_id}/comments", response_model=CommentOut, status_code=201)
def create_comment(
    post_id:      int,
    data:         CommentCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post nie istnieje")
    comment = Comment(content=data.content, author_id=current_user.id, post_id=post_id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id:   int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Komentarz nie istnieje")
    if current_user.role != "admin" and comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    db.delete(comment)
    db.commit()