from consoleplat.services.publish_orchestrator import PublishStage, StageOrchestrator


class DummyRecord:
    def __init__(self) -> None:
        self.task_id = "20260624120000"


class FakeScheduler:
    def __init__(self) -> None:
        self.pending: list[tuple[int, object]] = []

    def __call__(self, delay_seconds, callback):
        self.pending.append((int(delay_seconds), callback))
        return callback

    def fire_next(self) -> None:
        _delay, callback = self.pending.pop(0)
        callback()

    def fire_all(self) -> None:
        while self.pending:
            self.fire_next()


def test_orchestrator_waits_then_validates_and_launches():
    record = DummyRecord()
    scheduler = FakeScheduler()
    stages = []
    actions = []
    orchestrator = StageOrchestrator(
        schedule=scheduler,
        on_validate=lambda target: actions.append(("validate", target.task_id)) or True,
        on_launch=lambda target: actions.append(("launch", target.task_id)),
        on_stage_changed=lambda target, stage, countdown_seconds=None: stages.append((stage, countdown_seconds)),
    )

    orchestrator.begin_handoff(record, delay_seconds=2, pause_before_putaway=False)

    assert actions == []
    assert orchestrator.stage == PublishStage.WAITING_HANDOFF

    scheduler.fire_next()
    assert actions == []
    assert orchestrator.stage == PublishStage.WAITING_HANDOFF

    scheduler.fire_next()

    assert actions == [("validate", record.task_id), ("launch", record.task_id)]
    assert orchestrator.stage == PublishStage.DONE
    assert stages == [
        (PublishStage.WAITING_HANDOFF, 2),
        (PublishStage.WAITING_HANDOFF, 1),
        (PublishStage.VALIDATING, None),
        (PublishStage.LAUNCHING, None),
        (PublishStage.DONE, None),
    ]


def test_orchestrator_pause_and_resume_freezes_countdown():
    record = DummyRecord()
    scheduler = FakeScheduler()
    actions = []
    orchestrator = StageOrchestrator(
        schedule=scheduler,
        on_validate=lambda target: actions.append(("validate", target.task_id)) or True,
        on_launch=lambda target: actions.append(("launch", target.task_id)),
        on_stage_changed=lambda *_args, **_kwargs: None,
    )

    orchestrator.begin_handoff(record, delay_seconds=2, pause_before_putaway=False)
    orchestrator.pause()
    scheduler.fire_next()

    assert actions == []
    assert orchestrator.stage == PublishStage.WAITING_HANDOFF

    orchestrator.resume()
    scheduler.fire_all()

    assert actions == [("validate", record.task_id), ("launch", record.task_id)]
    assert orchestrator.stage == PublishStage.DONE


def test_orchestrator_waits_for_manual_launch_confirmation():
    record = DummyRecord()
    scheduler = FakeScheduler()
    actions = []
    stages = []
    orchestrator = StageOrchestrator(
        schedule=scheduler,
        on_validate=lambda target: actions.append(("validate", target.task_id)) or True,
        on_launch=lambda target: actions.append(("launch", target.task_id)),
        on_stage_changed=lambda target, stage, countdown_seconds=None: stages.append((stage, countdown_seconds)),
    )

    orchestrator.begin_handoff(record, delay_seconds=0, pause_before_putaway=True)

    assert actions == [("validate", record.task_id)]
    assert orchestrator.stage == PublishStage.PENDING_CONFIRM

    orchestrator.resume_launch()

    assert actions == [("validate", record.task_id), ("launch", record.task_id)]
    assert orchestrator.stage == PublishStage.DONE
    assert stages == [
        (PublishStage.VALIDATING, None),
        (PublishStage.PENDING_CONFIRM, None),
        (PublishStage.LAUNCHING, None),
        (PublishStage.DONE, None),
    ]


def test_orchestrator_abort_blocks_future_callbacks():
    record = DummyRecord()
    scheduler = FakeScheduler()
    actions = []
    orchestrator = StageOrchestrator(
        schedule=scheduler,
        on_validate=lambda target: actions.append(("validate", target.task_id)) or True,
        on_launch=lambda target: actions.append(("launch", target.task_id)),
        on_stage_changed=lambda *_args, **_kwargs: None,
    )

    orchestrator.begin_handoff(record, delay_seconds=1, pause_before_putaway=False)
    orchestrator.abort()
    scheduler.fire_all()

    assert actions == []
    assert orchestrator.stage == PublishStage.ABORTED


def test_orchestrator_marks_failed_when_validation_fails():
    record = DummyRecord()
    scheduler = FakeScheduler()
    actions = []
    stages = []
    orchestrator = StageOrchestrator(
        schedule=scheduler,
        on_validate=lambda target: actions.append(("validate", target.task_id)) or False,
        on_launch=lambda target: actions.append(("launch", target.task_id)),
        on_stage_changed=lambda target, stage, countdown_seconds=None: stages.append((stage, countdown_seconds)),
    )

    orchestrator.begin_handoff(record, delay_seconds=0, pause_before_putaway=False)

    assert actions == [("validate", record.task_id)]
    assert orchestrator.stage == PublishStage.FAILED
    assert ("launch", record.task_id) not in actions
    assert stages == [
        (PublishStage.VALIDATING, None),
        (PublishStage.FAILED, None),
    ]
