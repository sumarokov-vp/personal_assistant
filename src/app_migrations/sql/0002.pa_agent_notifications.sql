-- Журнал уведомлений рабочих агентов из RabbitMQ (очередь pa.notifications)

CREATE TABLE agent_notifications (
    id BIGSERIAL PRIMARY KEY,
    message_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    body TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ
);

CREATE INDEX agent_notifications_received_at_idx ON agent_notifications (received_at);
