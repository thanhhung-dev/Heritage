"""Create only the two R2 admin metadata tables; no migrations or R2 writes."""
import argparse
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

from apps.backend.models.knowledge import KnowledgeDocument, KnowledgeUpload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', default='.env')
    args = parser.parse_args()
    load_dotenv(args.env_file)
    url = os.environ.get('DATABASE_URL', '')
    if not url.startswith('postgresql+psycopg://'):
        raise SystemExit('Cần DATABASE_URL=postgresql+psycopg://... cho metadata knowledge.')
    engine = create_engine(url)
    try:
        KnowledgeDocument.metadata.create_all(engine, tables=[
            KnowledgeDocument.__table__, KnowledgeUpload.__table__], checkfirst=True)
    finally:
        engine.dispose()
    print('Đã tạo/kiểm tra knowledge_document và knowledge_upload; không thay bảng cũ hay R2.')


if __name__ == '__main__':
    main()
