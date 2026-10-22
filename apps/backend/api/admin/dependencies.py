"""Shared dependencies for local-only knowledge administration."""
import os

from fastapi import Depends, HTTPException, Request
from apps.backend.core.security import require_admin

from apps.backend.common.config import cors_origins
from apps.backend.common.db.base import AsyncSessionLocal
from apps.backend.common.services.knowledge import KnowledgeService
from apps.backend.common.storage.r2 import R2Storage


def local_only(request: Request):
    if os.environ.get('APP_ENVIRONMENT', 'local') not in {'local', 'test'}:
        raise HTTPException(403, 'API chưa có auth, chỉ được dùng trong môi trường local/test.')
    if (not request.client or request.client.host not in {'127.0.0.1', '::1'}
            or request.url.hostname not in {'localhost', '127.0.0.1', '::1'}):
        raise HTTPException(403, 'API quản trị chưa có auth, chỉ nhận kết nối loopback.')
    origin = request.headers.get('origin')
    if origin and origin not in [*cors_origins(), str(request.base_url).rstrip('/')]:
        raise HTTPException(403, 'Origin không được phép gọi API quản trị local.')


def get_storage():
    return R2Storage()


async def get_db():
    if AsyncSessionLocal.kw.get('bind') is None:
        raise HTTPException(503, 'Cần DATABASE_URL và tạo bảng knowledge để quản lý tài liệu/upload.')
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise HTTPException(503, 'Database knowledge không sẵn sàng; kiểm tra cấu hình/schema.') from None


def get_service(db=Depends(get_db), storage=Depends(get_storage)):
    return KnowledgeService(db, storage)
