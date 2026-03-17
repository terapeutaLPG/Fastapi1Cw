from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.deps import get_current_user
from auth.security import hash_password, verify_password
from database import get_db
from models.post import Post
from models.user import User
from schemas.post import PostOut
from schemas.user import PasswordChange, UserMeUpdate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
	return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
	data: UserMeUpdate,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	if data.username is None and data.email is None:
		raise HTTPException(status_code=400, detail="Podaj username lub email do aktualizacji")

	if data.username is not None and data.username != current_user.username:
		username_taken = (
			db.query(User)
			.filter(User.username == data.username, User.id != current_user.id)
			.first()
		)
		if username_taken:
			raise HTTPException(status_code=409, detail="Nazwa użytkownika już jest zajęta")
		current_user.username = data.username

	if data.email is not None and data.email != current_user.email:
		email_taken = (
			db.query(User)
			.filter(User.email == data.email, User.id != current_user.id)
			.first()
		)
		if email_taken:
			raise HTTPException(status_code=409, detail="Email jest zajęty")
		current_user.email = data.email

	db.add(current_user)
	db.commit()
	db.refresh(current_user)
	return current_user


@router.post("/me/change-password", status_code=204)
def change_password(
	data: PasswordChange,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	if not verify_password(data.current_password, current_user.hashed_password):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Aktualne hasło jest niepoprawne",
		)

	if data.current_password == data.new_password:
		raise HTTPException(status_code=400, detail="Nowe hasło musi być inne niż stare")

	current_user.hashed_password = hash_password(data.new_password)
	db.add(current_user)
	db.commit()


@router.get("/{user_id}/posts", response_model=list[PostOut])
def get_user_public_posts(user_id: int, db: Session = Depends(get_db)):
	user = db.get(User, user_id)
	if not user:
		raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")

	return (
		db.query(Post)
		.filter(Post.author_id == user_id, Post.published.is_(True))
		.all()
	)
