-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(225) NOT NULL UNIQUE,
    passwordhash VARCHAR(255) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title              VARCHAR(225) NOT NULL,
    description        VARCHAR(500),
    priority           VARCHAR(10) NOT NULL DEFAULT 'P3',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    estimated_minutes  INTEGER,
    remaining_minutes  INTEGER,
    is_done            BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted         BOOLEAN NOT NULL DEFAULT FALSE,
    created_by_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON tasks(created_by_id);
