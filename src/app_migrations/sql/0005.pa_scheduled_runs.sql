-- Журнал запусков по расписанию (сообщения schedule.due от assistant_scheduler): прогон модели и доставка владельцу

CREATE TABLE scheduled_runs (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    schedule_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    error TEXT
);

CREATE INDEX scheduled_runs_schedule_id_idx ON scheduled_runs (schedule_id);
