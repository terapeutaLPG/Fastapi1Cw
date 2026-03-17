# FastAPI — Baza danych i autoryzacja

> **Laboratorium 1.2** · Python · SQLAlchemy · JWT · RBAC
>
> *Od prostego CRUD-a do bezpiecznego API z autoryzacją*

---

```
// ROZDZIAŁ 01

Relacje w SQLAlchemy
Modele powiązane — one-to-many i many-to-many

────────────────────────────────────────
```

# Relacje między tabelami

W poprzednim laboratorium modele istniały niezależnie. W prawdziwych aplikacjach zasoby są powiązane — użytkownik posiada posty, post ma tagi, komentarz należy do użytkownika i postu. SQLAlchemy obsługuje te relacje deklaratywnie, przez `relationship()`.

## One-to-many (jeden do wielu)

Najpowszechniejszy wzorzec — jeden `User` ma wiele `Post`ów.

```python
# models/user.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    username       = Column(String(50), unique=True, nullable=False)
    email          = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role           = Column(String(20), default="user")  # "user" | "admin"

    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
```

```python
# models/post.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Post(Base):
    __tablename__ = "posts"

    id        = Column(Integer, primary_key=True, index=True)
    title     = Column(String(200), nullable=False)
    content   = Column(Text, nullable=False)
    published = Column(Boolean, default=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    author   = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
```

> **🔗 cascade="all, delete-orphan"**
>
> Gdy usuniesz użytkownika, SQLAlchemy automatycznie usunie też wszystkie jego posty. Bez `cascade` próba usunięcia użytkownika z postami zakończy się błędem klucza obcego.

## Many-to-many (wiele do wielu)

Posty mogą mieć wiele tagów, tagi mogą dotyczyć wielu postów. Potrzebna jest tabela pośrednia.

```python
# models/tag.py
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# Tabela asocjacyjna — bez własnej klasy modelu
post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id"), primary_key=True),
    Column("tag_id",  ForeignKey("tags.id"),  primary_key=True),
)

class Tag(Base):
    __tablename__ = "tags"

    id    = Column(Integer, primary_key=True, index=True)
    name  = Column(String(50), unique=True, nullable=False)

    posts = relationship("Post", secondary=post_tags, back_populates="tags")
```

```python
# Dodaj do models/post.py:
tags = relationship("Tag", secondary=post_tags, back_populates="posts")
```

## Inicjalizacja wszystkich tabel

```python
# main.py
from fastapi import FastAPI
from database import engine, Base
from models import user, post, tag  # import rejestruje modele w Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Blog API", version="1.2")
```

> **⚠️ Kolejność importów ma znaczenie**
>
> SQLAlchemy musi znać wszystkie modele zanim wywołasz `create_all()`. Importuj każdy moduł z modelem — nawet jeśli go nie używasz bezpośrednio.

---

```
// ROZDZIAŁ 02

Zaawansowane zapytania
Filtrowanie, wyszukiwanie, paginacja

────────────────────────────────────────
```

# Wzorce zapytań do bazy

## Filtrowanie i wyszukiwanie

```python
# routers/posts.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models.post import Post

router = APIRouter(prefix="/posts", tags=["posts"])

@router.get("/")
def list_posts(
    db:        Session = Depends(get_db),
    published: bool | None = Query(None,   description="Filtruj po statusie"),
    author_id: int  | None = Query(None,   description="Filtruj po autorze"),
    search:    str  | None = Query(None,   description="Szukaj w tytule i treści"),
    page:      int         = Query(1, ge=1, description="Numer strony"),
    per_page:  int         = Query(20, ge=1, le=100, description="Wyników na stronę"),
):
    query = db.query(Post)

    # Opcjonalne filtry — każdy dokładany tylko gdy podany
    if published is not None:
        query = query.filter(Post.published == published)
    if author_id is not None:
        query = query.filter(Post.author_id == author_id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            Post.title.ilike(pattern) | Post.content.ilike(pattern)
        )

    total  = query.count()
    items  = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    (total + per_page - 1) // per_page,
        "items":    items,
    }
```

## Eager loading — unikaj N+1

Domyślnie SQLAlchemy ładuje powiązane obiekty leniwie (lazy loading) — każdy dostęp do `post.author` generuje osobne zapytanie SQL. Przy liście 100 postów oznacza to 101 zapytań.

```python
from sqlalchemy.orm import joinedload, selectinload

# joinedload — jeden JOIN, dobre dla relacji one-to-one / many-to-one
posts = (
    db.query(Post)
    .options(joinedload(Post.author))   # załaduj autora od razu
    .all()
)

# selectinload — osobne IN-query, dobre dla kolekcji (one-to-many)
posts = (
    db.query(Post)
    .options(selectinload(Post.comments))  # załaduj komentarze od razu
    .all()
)

# Kombinacja
posts = (
    db.query(Post)
    .options(joinedload(Post.author), selectinload(Post.tags))
    .all()
)
```

> **📋 Kiedy używać czego**
>
> `joinedload` → relacja "jeden" (autor postu, kategoria produktu)
>
> `selectinload` → kolekcja (komentarze, tagi, zamówienia)
>
> Nie łącz `joinedload` z `limit()` — wyniki będą błędne. Użyj `selectinload`.

## Modele Pydantic z relacjami

```python
# schemas/post.py
from pydantic import BaseModel

class AuthorBasic(BaseModel):
    id:       int
    username: str

    model_config = {"from_attributes": True}

class TagOut(BaseModel):
    id:   int
    name: str

    model_config = {"from_attributes": True}

class PostCreate(BaseModel):
    title:     str
    content:   str
    published: bool = False
    tag_ids:   list[int] = []

class PostOut(BaseModel):
    id:        int
    title:     str
    content:   str
    published: bool
    author:    AuthorBasic
    tags:      list[TagOut] = []

    model_config = {"from_attributes": True}
```

---

```
// ROZDZIAŁ 03

Rejestracja i logowanie
Użytkownicy w bazie danych

────────────────────────────────────────
```

# Kompletny system użytkowników

## Schematy użytkownika

```python
# schemas/user.py
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    username: str       = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email:    EmailStr
    password: str       = Field(min_length=8)

class UserOut(BaseModel):
    id:       int
    username: str
    email:    str
    role:     str

    model_config = {"from_attributes": True}

class PasswordChange(BaseModel):
    current_password: str
    new_password:     str = Field(min_length=8)
```

## Logika rejestracji i logowania

```python
# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.user import UserCreate, UserOut
from auth.security import hash_password, verify_password, create_access_token, create_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    # Sprawdź unikalność
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email już jest zajęty")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=409, detail="Nazwa użytkownika już jest zajęta")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Niepoprawna nazwa użytkownika lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token  = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
    }
```

---

```
// ROZDZIAŁ 04

Tokeny JWT
Access token, refresh token, ochrona endpointów

────────────────────────────────────────
```

# Dwutokenowy system JWT

W produkcyjnych aplikacjach stosuje się dwa tokeny: krótkotrwały **access token** (15–30 minut) używany do autoryzacji oraz długotrwały **refresh token** (7–30 dni) pozwalający na wydanie nowego access tokenu bez ponownego logowania.

```
pip install "python-jose[cryptography]" passlib[bcrypt] "pydantic[email]"
```

## Konfiguracja i generowanie tokenów

```python
# auth/security.py
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY             = "zmien-na-losowy-ciag-w-produkcji"   # openssl rand -hex 32
REFRESH_SECRET_KEY     = "inny-sekret-dla-refresh-tokenow"
ALGORITHM              = "HS256"
ACCESS_TOKEN_EXPIRE    = timedelta(minutes=30)
REFRESH_TOKEN_EXPIRE   = timedelta(days=7)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def _create_token(data: dict, expire_delta: timedelta, secret: str) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expire_delta
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, secret, algorithm=ALGORITHM)

def create_access_token(data: dict) -> str:
    return _create_token(data, ACCESS_TOKEN_EXPIRE, SECRET_KEY)

def create_refresh_token(data: dict) -> str:
    return _create_token(data, REFRESH_TOKEN_EXPIRE, REFRESH_SECRET_KEY)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
```

> **🔑 Dlaczego dwa klucze?**
>
> Refresh token ma inny sekret niż access token, żeby skradziony access token nie mógł zostać użyty do wygenerowania nowego refresh tokenu. To minimalny poziom bezpieczeństwa wymagany w produkcji.

## Endpoint odświeżania tokenu

```python
# Dodaj do routers/auth.py
from pydantic import BaseModel
from jose import JWTError
from auth.security import decode_refresh_token

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh")
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_refresh_token(body.refresh_token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Nieprawidłowy refresh token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Użytkownik nie istnieje")

    new_access  = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = create_refresh_token({"sub": str(user.id)})

    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}
```

## Dependency — aktualny użytkownik

```python
# auth/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from database import get_db
from models.user import User
from auth.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nie można zweryfikować tożsamości",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = db.get(User, int(user_id))
    if user is None:
        raise credentials_error
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    # Tutaj można sprawdzić np. is_active / is_banned
    return current_user
```

---

```
// ROZDZIAŁ 05

Kontrola dostępu
Role użytkowników (RBAC)

────────────────────────────────────────
```

# Autoryzacja oparta na rolach

Uwierzytelnianie (*authentication*) to weryfikacja tożsamości — "kim jesteś?". Autoryzacja (*authorization*) to weryfikacja uprawnień — "co możesz zrobić?".

## Fabryka zależności ról

```python
# auth/deps.py (rozszerzenie)

def require_role(*allowed_roles: str):
    """
    Fabryka dependency — zwraca funkcję sprawdzającą rolę.

    Użycie:
        @router.delete("/{id}", dependencies=[Depends(require_role("admin"))])
    lub:
        current: User = Depends(require_role("admin", "moderator"))
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Wymagana rola: {' lub '.join(allowed_roles)}",
            )
        return current_user
    return role_checker

# Skróty dla wygody
require_admin = require_role("admin")
require_user  = require_role("user", "admin")  # admin też może to co user
```

## Właściciel zasobu vs. administrator

```python
# routers/posts.py (fragment)
from auth.deps import get_current_user, require_admin

@router.delete("/{post_id}", status_code=204)
def delete_post(
    post_id:      int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Nie znaleziono postu")

    # Admin może usunąć każdy post, właściciel — tylko swój
    if current_user.role != "admin" and post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Brak uprawnień do usunięcia tego postu")

    db.delete(post)
    db.commit()

@router.get("/admin/all", dependencies=[Depends(require_admin)])
def admin_list_all_posts(db: Session = Depends(get_db)):
    """Tylko admin widzi wszystkie posty — włącznie z niepublikowanymi."""
    return db.query(Post).all()
```

> **⚠️ Typowe błędy autoryzacji**
>
> Sprawdzanie roli tylko w UI (frontendzie) — backend musi weryfikować sam.
>
> Użycie ID z URL zamiast z tokenu — atakujący może podmienić ID w zapytaniu.
>
> Brak sprawdzenia właściciela zasobu — użytkownik A edytuje dane użytkownika B.

---

```
// ROZDZIAŁ 06

Zaawansowana obsługa błędów
Spójne odpowiedzi, walidacja, middleware

────────────────────────────────────────
```

# Spójne komunikaty błędów

## Standardowy format odpowiedzi błędu

```python
# exceptions.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    status:  int
    error:   str
    detail:  str | list | None = None
    path:    str | None = None

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                status=exc.status_code,
                error=exc.detail if isinstance(exc.detail, str) else "HTTP Error",
                path=str(request.url),
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = [
            {"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                status=422,
                error="Błąd walidacji danych",
                detail=errors,
                path=str(request.url),
            ).model_dump(),
        )
```

```python
# main.py
from exceptions import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
```

## Middleware — logowanie requestów

```python
# main.py
import time
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)

    print(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")
    response.headers["X-Process-Time"] = str(duration)
    return response
```

---

```
// ROZDZIAŁ 07

Pełna struktura projektu
Scalamy wszystko razem

────────────────────────────────────────
```

# Struktura kompletnego projektu

```
blog-api/
├── main.py                  # FastAPI app, rejestracja routerów i handlerów
├── database.py              # engine, SessionLocal, get_db
├── exceptions.py            # globalne handlery błędów
│
├── auth/
│   ├── security.py          # hash, verify, create/decode token
│   └── deps.py              # get_current_user, require_role
│
├── models/
│   ├── __init__.py          # import wszystkich modeli (ważne dla create_all!)
│   ├── user.py
│   ├── post.py
│   └── tag.py
│
├── schemas/
│   ├── user.py              # UserCreate, UserOut, PasswordChange
│   ├── post.py              # PostCreate, PostOut, PostUpdate
│   └── token.py             # TokenResponse, RefreshRequest
│
├── routers/
│   ├── auth.py              # /auth/register, /auth/token, /auth/refresh
│   ├── users.py             # /users/me, /users/{id}
│   └── posts.py             # /posts — pełny CRUD z autoryzacją
│
└── requirements.txt
```

```
# requirements.txt
fastapi[standard]
sqlalchemy
python-jose[cryptography]
passlib[bcrypt]
pydantic[email]
```

## Kompletny main.py

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from models import user, post, tag  # rejestracja modeli
from routers import auth, users, posts
from exceptions import register_exception_handlers

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Blog API",
    version="1.2",
    description="REST API z autoryzacją JWT i kontrolą dostępu",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
```

---

```
// ROZDZIAŁ 08

Ćwiczenia
Zadania do samodzielnego wykonania

────────────────────────────────────────
```

# Ćwiczenia laboratoryjne

> **📌 Wskazówka**
>
> Zacznij od skopiowania struktury projektu z Rozdziału 07. Każde ćwiczenie rozbudowuje projekt o kolejną warstwę. Testuj na bieżąco przez Swagger UI pod `/docs`.

## Ćwiczenie 1 — Model komentarzy

Rozbuduj projekt o zasób `Comment` powiązany z `Post` i `User`.

1. Zdefiniuj model SQLAlchemy `Comment` z polami: `id`, `content`, `author_id`, `post_id`, `created_at`
2. Dodaj relację `comments` do modelu `Post` (one-to-many z cascade)
3. Stwórz endpointy: `GET /posts/{id}/comments`, `POST /posts/{id}/comments` (wymaga logowania)
4. Endpoint DELETE `/comments/{id}` — tylko autor komentarza lub admin może usunąć

## Ćwiczenie 2 — Profil użytkownika

Dodaj endpointy zarządzania własnym kontem.

1. `GET /users/me` — zwraca dane zalogowanego użytkownika (wymaga tokenu)
2. `PATCH /users/me` — aktualizacja email lub username (sprawdź unikalność!)
3. `POST /users/me/change-password` — przyjmuje `current_password` i `new_password`, weryfikuje stare hasło przed zmianą
4. `GET /users/{id}/posts` — publiczne posty wybranego użytkownika (bez autoryzacji)

## Ćwiczenie 3 — Tagi i wyszukiwanie

Zaimplementuj system tagów i rozbudowane wyszukiwanie.

1. Endpointy `GET /tags`, `POST /tags` (tylko admin), `DELETE /tags/{id}` (tylko admin)
2. Przy tworzeniu posta przyjmuj `tag_ids: list[int]` i przypisuj tagi przez relację many-to-many
3. Endpoint `GET /posts?tag=python` — filtrowanie postów po nazwie tagu
4. Endpoint `GET /posts?search=fastapi` — wyszukiwanie pełnotekstowe w tytule i treści (case-insensitive)

---

> **🏆 Mini-projekt — Kompletne API bloga**
>
> Połącz ćwiczenia 1–3 w jeden projekt z pełną dokumentacją Swagger.
>
> Wymagania: rejestracja i logowanie, refresh token, role admin/user, pełny CRUD postów i komentarzy, tagi, paginacja, wyszukiwanie.
>
> Zaimportuj projekt do Insomnia lub Postman i przetestuj cały przepływ: rejestracja → logowanie → tworzenie posta → dodanie komentarza → usunięcie przez admina.

---

```
// ROZDZIAŁ 09

Ściągawka
Wzorce, kody statusów, przydatne linki

────────────────────────────────────────
```

# Ściągawka — Lab 1.2

## Wzorce dependency injection

| Scenariusz            | Dependency                                    |
|-----------------------|-----------------------------------------------|
| Sesja bazy danych     | `db: Session = Depends(get_db)`               |
| Zalogowany użytkownik | `user: User = Depends(get_current_user)`      |
| Tylko admin           | `Depends(require_role("admin"))`              |
| Admin lub moderator   | `Depends(require_role("admin", "moderator"))` |
| Właściciel lub admin  | Logika w ciele endpointu                      |

## Kody statusów HTTP

| Kod     | Nazwa                | Kiedy użyć                  |
|---------|----------------------|-----------------------------|
| **200** | OK                   | GET, PATCH — sukces         |
| **201** | Created              | POST — nowy zasób           |
| **204** | No Content           | DELETE — brak body          |
| **400** | Bad Request          | Błąd logiki / złe dane      |
| **401** | Unauthorized         | Brak / wygasły token        |
| **403** | Forbidden            | Brak uprawnień              |
| **404** | Not Found            | Zasób nie istnieje          |
| **409** | Conflict             | Duplikat (e-mail, username) |
| **422** | Unprocessable Entity | Błąd walidacji Pydantic     |

## Przydatne komendy

```bash
# Generowanie bezpiecznego klucza JWT
openssl rand -hex 32

# Uruchomienie serwera
uvicorn main:app --reload --port 8000

# Inspekcja bazy SQLite
sqlite3 app.db ".tables"
sqlite3 app.db "SELECT * FROM users;"

# Testy — już w Lab 1.3
pytest tests/ -v --tb=short
```

## Przydatne linki

- <https://fastapi.tiangolo.com/tutorial/security/> — oficjalny tutorial autoryzacji
- <https://docs.sqlalchemy.org/en/20/orm/relationships.html> — relacje SQLAlchemy
- <https://jwt.io> — debugger tokenów JWT
- <https://docs.pydantic.dev/latest/> — dokumentacja Pydantic v2
- <https://bcrypt-generator.com> — generator hashy bcrypt do testów

---

*Kolejne laboratorium (1.3) — programowanie asynchroniczne, WebSocket, testy jednostkowe z pytest i konteneryzacja Docker.*

---

*FastAPI · SQLAlchemy · JWT · RBAC*