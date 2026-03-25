from typing import List
import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.database import Task, User
from app.schemas.auth import TaskCreate


class TaskService:

    def create_task(self, data: TaskCreate, owner: User, db: Session) -> Task:
        task = Task(
            title=data.title,
            description=data.description,
            priority=data.priority,
            estimated_minutes=data.estimated_minutes,
            # remaining_minutes is NOT stored — computed dynamically on every read
            created_by_id=owner.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def get_tasks_for_user(self, owner: User, db: Session) -> List[Task]:
        return (
            db.query(Task)
            .filter(Task.created_by_id == owner.id, Task.is_deleted == False)
            .order_by(Task.created_at.desc())
            .all()
        )

    def mark_done(self, task_id: uuid.UUID, owner: User, db: Session) -> Task:
        task = self._get_task_or_404(task_id, owner, db)
        task.is_done = True
        db.commit()
        db.refresh(task)
        return task

    def delete_task(self, task_id: uuid.UUID, owner: User, db: Session) -> None:
        task = self._get_task_or_404(task_id, owner, db)
        task.is_deleted = True
        db.commit()

    def _get_task_or_404(self, task_id: uuid.UUID, owner: User, db: Session) -> Task:
        task = (
            db.query(Task)
            .filter(
                Task.id == task_id,
                Task.created_by_id == owner.id,
                Task.is_deleted == False,
            )
            .first()
        )
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task


task_service = TaskService()
