from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models.task import Task
from schemas.task import TaskCreate, TaskOut, TaskPut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["todo-list"])


@router.get("/", response_model=list[TaskOut], summary="Pobierz todo-list")
def list_tasks(
    done: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Task).order_by(Task.created_at.desc(), Task.id.desc())
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
    return query.all()


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED, summary="Dodaj element do todo-list")
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    task = Task(
        title=data.title.strip(),
        description=data.description.strip() if data.description else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut, summary="Pobierz pojedynczy element todo-list")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")
    return task


@router.put("/{task_id}", response_model=TaskOut, summary="Pełna aktualizacja elementu todo-list")
def replace_task(task_id: int, data: TaskPut, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")

    task.title = data.title.strip()
    task.description = data.description.strip() if data.description else None
    task.done = data.done
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut, summary="Zmień status elementu todo-list")
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")

    task.done = data.done
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/toggle", response_model=TaskOut, summary="Przełącz status done elementu todo-list")
def toggle_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")

    task.done = not task.done
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Usuń element z todo-list")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")

    db.delete(task)
    db.commit()
