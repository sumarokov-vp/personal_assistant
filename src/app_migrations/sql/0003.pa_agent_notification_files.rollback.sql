ALTER TABLE agent_notifications
    DROP COLUMN IF EXISTS file_size,
    DROP COLUMN IF EXISTS file_name;
