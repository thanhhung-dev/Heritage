# Conversation migration

The current `AdminAccount` class maps to `account.id` (integer). Conversation
ownership references that table rather than creating a second authentication
table named `admin_account`.

Revision `20261026_chat` extends the existing application schema. It adds
`conversation`, `message_citation`, and an optional `chat_message.conversation_id`.
Legacy messages keep their existing `session_id`, citations and feedback. Each
message must belong to exactly one legacy session or one conversation.

Revision `20261028_search_sync` follows the chat revision and adds nullable
account audit fields, `scene.camera_path_url`, sky scattering/cloud/star fields
and interactive explore text. It uses `ADD COLUMN IF NOT EXISTS` to support
databases that already ran the standalone camera/sky SQL scripts. It does not
seed or overwrite existing content. Downgrade requires a reviewed manual plan
because the fields may predate Alembic tracking and contain authored data.

Revision `20261028_knowledge` creates the R2 document/upload metadata tables used
by the registered local knowledge administration router. Existing tables and
objects are preserved; applying the migration never contacts the R2 bucket.

After approval, apply the latest schema from `apps/backend`:

```powershell
python -m alembic upgrade head
python -m alembic current
```

Alembic is declared in the backend requirements. From the repository root,
generate SQL for review without connecting:

```powershell
python -m alembic -c apps/backend/alembic.ini upgrade head --sql
```

Set `DATABASE_URL` in the environment or the root `.env`. Do not apply this
migration to an existing environment without approval. The first revision assumes
the account, heritage and legacy chat tables already exist; it does not bootstrap
a blank database. Downgrade refuses to remove conversation messages or citations.
