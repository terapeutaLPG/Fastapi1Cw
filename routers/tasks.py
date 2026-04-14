from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.task import Task
from schemas.task import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["todo-list"])


@router.get("/", response_model=list[TaskOut], summary="Pobierz todo-list")
def list_tasks(
    done: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Task).order_by(Task.created_at.desc(), Task.id.desc())
    if done is not None:
        query = query.filter(Task.done == done)
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


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Usuń element z todo-list")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Zadanie nie istnieje")

    db.delete(task)
    db.commit()
