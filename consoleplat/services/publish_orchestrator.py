from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class PublishStage(str, Enum):
    GENERATING = "generating"
    WAITING_HANDOFF = "waiting_handoff"
    VALIDATING = "validating"
    PENDING_CONFIRM = "pending_confirm"
    LAUNCHING = "launching"
    DONE = "done"
    ABORTED = "aborted"
    FAILED = "failed"


@dataclass
class _ScheduledTask:
    token: object
    active: bool = True


class StageOrchestrator:
    def __init__(
        self,
        *,
        schedule: Callable[[int, Callable[[], None]], object | None],
        on_validate: Callable[[object], bool],
        on_launch: Callable[[object], None],
        on_stage_changed: Callable[[object, PublishStage], None] | Callable[[object, PublishStage, int | None], None],
    ) -> None:
        self._schedule = schedule
        self._on_validate = on_validate
        self._on_launch = on_launch
        self._on_stage_changed = on_stage_changed
        self._scheduled_tasks: list[_ScheduledTask] = []
        self._record: object | None = None
        self._paused = False
        self._aborted = False
        self._remaining_seconds = 0
        self.stage: PublishStage | None = None
        self._pause_before_putaway = False

    def begin_handoff(self, record, *, delay_seconds: int, pause_before_putaway: bool) -> None:
        self._reset_runtime_state()
        self._record = record
        self._pause_before_putaway = bool(pause_before_putaway)
        self._remaining_seconds = max(0, int(delay_seconds or 0))
        if self._remaining_seconds > 0:
            self._set_stage(PublishStage.WAITING_HANDOFF, countdown_seconds=self._remaining_seconds)
            self._schedule_wait_tick()
            return
        self._run_validate_and_continue()

    def pause(self) -> None:
        if self.stage == PublishStage.WAITING_HANDOFF and not self._aborted:
            self._paused = True

    def resume(self) -> None:
        if self._aborted:
            return
        if self.stage == PublishStage.WAITING_HANDOFF and self._paused:
            self._paused = False
            self._schedule_wait_tick()
            return
        if self.stage == PublishStage.PENDING_CONFIRM:
            self.resume_launch()

    def resume_launch(self) -> None:
        if self._aborted or self.stage != PublishStage.PENDING_CONFIRM or self._record is None:
            return
        self._launch()

    def abort(self) -> None:
        if self._aborted:
            return
        self._aborted = True
        self._paused = False
        self._cancel_pending_tasks()
        if self._record is not None:
            self._set_stage(PublishStage.ABORTED)

    def _reset_runtime_state(self) -> None:
        self._cancel_pending_tasks()
        self._paused = False
        self._aborted = False
        self._remaining_seconds = 0
        self.stage = None

    def _cancel_pending_tasks(self) -> None:
        for task in self._scheduled_tasks:
            task.active = False
        self._scheduled_tasks.clear()

    def _schedule_wait_tick(self) -> None:
        if self._aborted or self._record is None:
            return
        scheduled_task = _ScheduledTask(token=object())

        def callback() -> None:
            if self._aborted or not scheduled_task.active or self._record is None:
                return
            if self._paused:
                return
            if self._remaining_seconds <= 1:
                self._remaining_seconds = 0
                self._remove_task(scheduled_task)
                self._run_validate_and_continue()
                return
            self._remaining_seconds -= 1
            self._set_stage(PublishStage.WAITING_HANDOFF, countdown_seconds=self._remaining_seconds)
            self._remove_task(scheduled_task)
            self._schedule_wait_tick()

        scheduled_task.token = self._schedule(1, callback)
        self._scheduled_tasks.append(scheduled_task)

    def _remove_task(self, scheduled_task: _ScheduledTask) -> None:
        scheduled_task.active = False
        self._scheduled_tasks = [item for item in self._scheduled_tasks if item is not scheduled_task]

    def _run_validate_and_continue(self) -> None:
        if self._aborted or self._record is None:
            return
        self._set_stage(PublishStage.VALIDATING)
        ok = bool(self._on_validate(self._record))
        if self._aborted:
            return
        if not ok:
            self._set_stage(PublishStage.FAILED)
            return
        if self._pause_before_putaway:
            self._set_stage(PublishStage.PENDING_CONFIRM)
            return
        self._launch()

    def _launch(self) -> None:
        if self._aborted or self._record is None:
            return
        self._set_stage(PublishStage.LAUNCHING)
        self._on_launch(self._record)
        if self._aborted:
            return
        self._set_stage(PublishStage.DONE)

    def _set_stage(self, stage: PublishStage, *, countdown_seconds: int | None = None) -> None:
        self.stage = stage
        if self._record is None:
            return
        self._on_stage_changed(self._record, stage, countdown_seconds=countdown_seconds)
