"""Reset local identity tables to account/roles/profiles and seed demo users."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()
from sqlalchemy import create_engine, text

from apps.backend.core.security import hash_password


SCHEMA_SQL = """
DROP TABLE IF EXISTS admin_account CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS user_milestone_task CASCADE;
DROP TABLE IF EXISTS milestone_task_definition CASCADE;
DROP TABLE IF EXISTS milestone_level_definition CASCADE;
DROP TABLE IF EXISTS user_badge CASCADE;
DROP TABLE IF EXISTS badge_definition CASCADE;
DROP TABLE IF EXISTS user_consent CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
DROP TABLE IF EXISTS account CASCADE;

CREATE TABLE roles (
    id BIGINT PRIMARY KEY,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    name VARCHAR(50) NOT NULL UNIQUE,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    updated_by VARCHAR(100)
);

CREATE TABLE account (
    id BIGINT PRIMARY KEY,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    email VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    locked_until TIMESTAMP(6) WITH TIME ZONE,
    password_hash VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    updated_by VARCHAR(100),
    username VARCHAR(255) NOT NULL UNIQUE,
    role_id BIGINT REFERENCES roles(id) ON DELETE RESTRICT
);

CREATE TABLE profiles (
    account_id BIGINT PRIMARY KEY REFERENCES account(id) ON DELETE CASCADE,
    about TEXT,
    address VARCHAR(255),
    avatar_url VARCHAR(255),
    dob DATE,
    full_name VARCHAR(255),
    gender BOOLEAN,
    personal_link VARCHAR(255),
    phone_number INTEGER,
    province_code VARCHAR(255),
    title VARCHAR(255)
);

CREATE TABLE user_consent (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL UNIQUE REFERENCES account(id) ON DELETE CASCADE,
    analytics_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE TABLE badge_definition (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    icon_key VARCHAR(50) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE user_badge (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES account(id) ON DELETE CASCADE,
    badge_id INTEGER NOT NULL REFERENCES badge_definition(id) ON DELETE CASCADE,
    earned_at DATE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (account_id, badge_id)
);

CREATE TABLE milestone_level_definition (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    level_name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE milestone_task_definition (
    id SERIAL PRIMARY KEY,
    level_id INTEGER NOT NULL REFERENCES milestone_level_definition(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE user_milestone_task (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES account(id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL REFERENCES milestone_task_definition(id) ON DELETE CASCADE,
    completed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (account_id, task_id)
);

CREATE INDEX idx_account_email ON account(email);
CREATE INDEX idx_account_username ON account(username);
CREATE INDEX idx_account_role_id ON account(role_id);
"""


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text(SCHEMA_SQL))
        connection.execute(
            text(
                "INSERT INTO roles (id, name, created_by) VALUES "
                "(1, 'USER', 'local-seed'), (2, 'ADMIN', 'local-seed')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO account "
                "(id, created_by, email, is_active, password_hash, username, role_id) "
                "VALUES (:id, 'local-seed', :email, TRUE, :password_hash, :username, :role_id)"
            ),
            [
                {
                    "id": 1,
                    "email": "admin@example.com",
                    "username": "admin",
                    "password_hash": hash_password("Admin@123456"),
                    "role_id": 2,
                },
                {
                    "id": 2,
                    "email": "demo@example.com",
                    "username": "demo",
                    "password_hash": hash_password("User@123456"),
                    "role_id": 1,
                },
            ],
        )
        connection.execute(
            text(
                "INSERT INTO profiles (account_id, full_name, title, province_code) "
                "VALUES "
                "(1, 'Heritage Admin', 'Administrator', 'DN'), "
                "(2, 'Demo User', 'Visitor', 'HUE')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO user_consent (account_id) VALUES (1), (2)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO badge_definition (code, title, description, icon_key, sort_order) "
                "VALUES "
                "('first-explorer', 'First Explorer', 'Completed your first heritage journey.', 'compass', 1), "
                "('heritage-fan', 'Heritage Fan', 'Explored multiple heritage stories.', 'heart', 2)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO milestone_level_definition (code, level_name, description, sort_order) "
                "VALUES ('beginner', 'Newcomer', 'Begin your heritage journey.', 0), "
                "('explorer', 'Explorer', 'Expand your heritage journey.', 1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO milestone_task_definition (level_id, code, title, sort_order) "
                "VALUES (1, 'visit-first-site', 'Explore your first site', 1), "
                "(2, 'read-heritage-story', 'Read a heritage story', 1)"
            )
        )
    engine.dispose()
    print("Local identity reset complete: roles, account, profiles seeded")


if __name__ == "__main__":
    main()
