from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database import User, Task
from app.schemas.auth import TaskCreate, TaskResponse
from app.services.jwt import get_current_user
from app.services.tasks import task_service
from opentelemetry import metrics

router = APIRouter()
meter = metrics.get_meter("app.api.endpoints.todos")

tasks_created=meter.create_counter("todo.tasks.created", description="Tasks created")

# IST offset — must match the offset used in models/database.py
IST = timezone(timedelta(hours=5, minutes=30))


def _compute_remaining(task: Task) -> Optional[int]:
    """
    Dynamically compute how many minutes remain of the estimate.

    Logic:
      elapsed_minutes = (now_IST - created_at_IST).total_seconds() / 60
      remaining       = estimated_minutes - elapsed_minutes
      clamped to 0 (never negative), None when no estimate exists.
    """
    if task.estimated_minutes is None:
        return None

    if task.is_done:
        # Once marked done the timer stops — show 0 remaining
        return 0

    now_ist = datetime.now(IST)

    # created_at is timezone-aware (stored in IST), so subtraction is safe
    created_ist = task.created_at.astimezone(IST)
    elapsed_seconds = (now_ist - created_ist).total_seconds()
    elapsed_minutes = int(elapsed_seconds / 60)

    remaining = task.estimated_minutes - elapsed_minutes
    return max(remaining, 0)   # clamp — never return negative


def _to_response(task: Task) -> TaskResponse:
    remaining = _compute_remaining(task)
    is_time_up = (
        remaining is not None          # has an estimate
        and remaining == 0             # time has elapsed
        and not task.is_done           # not yet marked done
    )

    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        created_by_username=task.owner.name,
        created_at=task.created_at.astimezone(IST),   # always return as IST
        estimated_minutes=task.estimated_minutes,
        remaining_minutes=remaining,
        is_time_up=is_time_up,
        is_done=task.is_done,
    )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = task_service.create_task(payload, current_user, db)
    tasks_created.add(1, attributes={"priority": payload.priority, "has_estimate": payload.estimated_minutes is not None})
    return _to_response(task)


@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = task_service.get_tasks_for_user(current_user, db)
    return [_to_response(t) for t in tasks]


@router.patch("/{task_id}/done", response_model=TaskResponse)
def mark_task_done(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = task_service.mark_done(task_id, current_user, db)
    return _to_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_service.delete_task(task_id, current_user, db)
