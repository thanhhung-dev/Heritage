"""Read only explicitly linked, reviewed KG evidence; never scan source corpora."""
from sqlalchemy import select

from apps.backend.models.kg import Entity
from apps.backend.services.heritage_classifier import ContentInput, normalize


async def classification_input(db, content):
    reviewed = ""
    hint = content.entity_type_hint
    if content.knowledge_entity_id:
        entity = await db.get(Entity, content.knowledge_entity_id)
        if (entity and entity.entry_status in {"reviewed", "published"}
                and (entity.source_document_id or entity.source_passage_id)
                and normalize(entity.name) == normalize(content.title)):
            reviewed = entity.summary or ""
            if content.source_url and not hint:
                hint = entity.type
    return ContentInput(content.title, content.tagline or "", content.headline or "", content.description or "",
                        hint, content.source_url, reviewed)
