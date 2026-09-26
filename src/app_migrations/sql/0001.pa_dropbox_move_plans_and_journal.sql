-- Планы переносов Dropbox и журнал операций для отката

CREATE TABLE dropbox_move_plans (
    id UUID PRIMARY KEY,
    owner_id BIGINT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('proposed', 'executed', 'rolled_back', 'cancelled')),
    moves JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE dropbox_journal (
    id BIGSERIAL PRIMARY KEY,
    plan_id UUID REFERENCES dropbox_move_plans(id),
    action TEXT NOT NULL
        CHECK (action IN ('added', 'moved', 'move_rolled_back', 'rollback_skipped')),
    source TEXT,
    target TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX dropbox_journal_plan_id_idx ON dropbox_journal (plan_id, id);
