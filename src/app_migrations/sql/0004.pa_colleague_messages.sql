-- Журнал почты ассистентов (exchange assistant-mail, ящик inbox.<ключ>): входящие и исходящие

CREATE TABLE colleague_messages (
    id BIGSERIAL PRIMARY KEY,
    message_id TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('in', 'out')),
    peer TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('remark', 'question', 'answer')),
    text TEXT NOT NULL,
    about_agent TEXT,
    in_reply_to TEXT,
    sent_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    shown_at TIMESTAMPTZ,
    UNIQUE (message_id, direction)
);

CREATE INDEX colleague_messages_received_at_idx
    ON colleague_messages (received_at)
    WHERE direction = 'in';
