from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth.deps import get_current_user
from database import get_db
from models.task import Task
from models.user import User
from schemas.task import TaskCreate, TaskListResponse, TaskOut, TaskPatch, TaskPut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["todo-list"])


def _scoped_tasks_query(db: Session, current_user: User):
    query = db.query(Task)
    if current_user.role != "admin":
        query = query.filter(Task.owner_id == current_user.id)
    return query


def _ensure_can_access(task: Task, current_user: User):
    if current_user.role != "admin" and task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień do tego zadania",
        )


@router.get("/", response_model=TaskListResponse, summary="Pobierz todo-list")
def list_tasks(
    done: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _scoped_tasks_query(db, current_user)
    if done is not None:
        query = query.filter(Task.done == done)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(pattern),
                Task.description.ilike(pattern),
            )
        )
    total = query.count()
    items = (
        query.order_by(Task.created_at.desc(), Task.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if total else 0,
        "items": items,
    }


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED, summary="Dodaj element do todo-list")
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(
        title=data.title.strip(),
        description=data.description.strip() if data.description else None,
        owner_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut, summary="Pobierz pojedynczy element todo-list")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")
    _ensure_can_access(task, current_user)
    return task


@router.put("/{task_id}", response_model=TaskOut, summary="Pełna aktualizacja elementu todo-list")
def replace_task(
    task_id: int,
    data: TaskPut,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")
    _ensure_can_access(task, current_user)

    task.title = data.title.strip()
    task.description = data.description.strip() if data.description else None
    task.done = data.done
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut, summary="Częściowa aktualizacja elementu todo-list")
def update_task(
    task_id: int,
    data: TaskPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")
    _ensure_can_access(task, current_user)

    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Brak danych do aktualizacji")

    if "title" in payload:
        task.title = payload["title"].strip()
    if "description" in payload:
        task.description = payload["description"].strip() if payload["description"] else None
    if "done" in payload:
        task.done = payload["done"]

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/toggle", response_model=TaskOut, summary="Przełącz status done elementu todo-list")
def toggle_task(
    task_id: int,
    data: TaskUpdate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")
    _ensure_can_access(task, current_user)

    if data is not None:
        task.done = data.done
    else:
        task.done = not task.done
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Usuń element z todo-list")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")
    _ensure_can_access(task, current_user)

    db.delete(task)
    db.commit()
