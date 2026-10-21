"""Bounded R2 object operations for the local knowledge administration API."""
from __future__ import annotations

import codecs
import os
from pathlib import PurePosixPath

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException


FILE_TYPES = {
    '.txt': 'text/plain', '.md': 'text/markdown',
    '.html': 'text/html', '.pdf': 'application/pdf',
}


def safe_name(value: str) -> str:
    if (not value or value != value.strip() or value in {'.', '..'}
            or len(value.encode()) > 255
            or any(c in value for c in '/\\%?#"')
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise HTTPException(422, 'Tên file/folder không hợp lệ.')
    return value


def knowledge_prefix(value: str | None = None, *, allow_root=True) -> str:
    root = os.environ.get('R2_KNOWLEDGE_PREFIX', 'curated/')
    for candidate in (root, value if value is not None else root):
        if (not candidate.endswith('/') or candidate.startswith('/')
                or any(not part or part in {'.', '..'} for part in candidate[:-1].split('/'))
                or any(c in candidate for c in '\\%?#')
                or any(ord(c) < 32 or ord(c) == 127 for c in candidate)):
            raise HTTPException(422, 'Prefix không hợp lệ; cần đường dẫn kết thúc bằng /.')
    value = root if value is None else value
    if not value.startswith(root) or (not allow_root and value == root):
        raise HTTPException(422, 'Không được thao tác ngoài prefix tri thức hoặc sửa folder gốc.')
    return value


class R2Storage:
    def __init__(self, *, client=None, bucket=None):
        self.bucket = bucket or os.environ.get('R2_BUCKET', '')
        if not self.bucket:
            raise HTTPException(503, 'Thiếu cấu hình R2_BUCKET.')
        if client is None:
            required = ('R2_ENDPOINT_URL', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY')
            if not all(os.environ.get(k) for k in required):
                raise HTTPException(503, 'Thiếu cấu hình endpoint/access key R2.')
            client = boto3.client(
                's3', endpoint_url=os.environ['R2_ENDPOINT_URL'],
                aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
                aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'], region_name='auto',
                config=Config(signature_version='s3v4', connect_timeout=5, read_timeout=30,
                              retries={'max_attempts': 2}, s3={'addressing_style': 'path'}),
            )
        self.client = client

    def call(self, method, **kwargs):
        try:
            return getattr(self.client, method)(Bucket=self.bucket, **kwargs)
        except ClientError as error:
            code = error.response.get('Error', {}).get('Code')
            if code in {'404', 'NoSuchKey', 'NotFound'}:
                raise HTTPException(404, 'Không tìm thấy object trên R2.') from None
            if code in {'PreconditionFailed', '412'}:
                raise HTTPException(409, 'Object đã thay đổi; tạo lại phiên upload.') from None
            raise HTTPException(503, 'R2 không khả dụng hoặc không đủ quyền thao tác.') from None
        except BotoCoreError:
            raise HTTPException(503, 'Không kết nối được R2.') from None

    def entries(self, prefix, limit, cursor=None, *, children_limit=100, expand_children=True):
        prefix = knowledge_prefix(prefix)
        options = {'Prefix': prefix, 'Delimiter': '/', 'MaxKeys': limit}
        if cursor:
            options['ContinuationToken'] = cursor
        page = self.call('list_objects_v2', **options)
        entries = [{'kind': 'folder', 'key': p['Prefix'],
                    'name': p['Prefix'][len(prefix):].rstrip('/')} for p in page.get('CommonPrefixes', [])]
        entries.extend({'kind': 'file', 'key': row['Key'], 'name': row['Key'][len(prefix):],
                        'size_bytes': row['Size'], 'updated_at': row['LastModified'].isoformat()}
                       for row in page.get('Contents', []) if row['Key'] != prefix)
        if expand_children:
            for entry in entries:
                if entry['kind'] == 'folder':
                    child_page = self.entries(entry['key'], children_limit, expand_children=False)
                    entry['children'] = child_page['entries']
                    entry['children_next_cursor'] = child_page['next_cursor']
        return {'prefix': prefix, 'entries': entries, 'next_cursor': page.get('NextContinuationToken')}

    def create_folder(self, parent_prefix, name):
        key = knowledge_prefix(parent_prefix) + safe_name(name) + '/'
        if self.call('list_objects_v2', Prefix=key, MaxKeys=1).get('Contents'):
            raise HTTPException(409, 'Folder đã tồn tại.')
        self.call('put_object', Key=key, Body=b'')
        return {'prefix': key}

    def empty_folder(self, prefix):
        prefix = knowledge_prefix(prefix, allow_root=False)
        page = self.call('list_objects_v2', Prefix=prefix, MaxKeys=2)
        if page.get('IsTruncated') or any(row['Key'] != prefix for row in page.get('Contents', [])):
            raise HTTPException(409, 'Chỉ cho đổi tên/xóa folder rỗng; không xóa đệ quy.')
        if not page.get('Contents'):
            raise HTTPException(404, 'Không tìm thấy folder rỗng.')
        return prefix

    def rename_folder(self, prefix, name):
        prefix = self.empty_folder(prefix)
        parent = prefix[:-1].rsplit('/', 1)[0] + '/'
        result = self.create_folder(parent, name)
        self.call('delete_object', Key=prefix)
        return result

    def delete_folder(self, prefix):
        self.call('delete_object', Key=self.empty_folder(prefix))

    def presign(self, method, key, *, content_type=None, filename=None):
        params = {'Bucket': self.bucket, 'Key': key}
        if content_type:
            params['ContentType'] = content_type
        if filename:
            from urllib.parse import quote
            params['ResponseContentDisposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
        try:
            return self.client.generate_presigned_url(method, Params=params, ExpiresIn=600)
        except BotoCoreError:
            raise HTTPException(503, 'Không tạo được URL R2.') from None

    def verify_upload(self, key, filename, size, content_type):
        head = self.call('head_object', Key=key)
        if head['ContentLength'] != size or head.get('ContentType', '').split(';')[0] != content_type:
            raise HTTPException(422, 'Dung lượng hoặc content type không khớp phiên upload.')
        body = self.call('get_object', Key=key, Range='bytes=0-4095', IfMatch=head['ETag'])['Body']
        try:
            sample = body.read(4096)
        finally:
            body.close()
        if PurePosixPath(filename).suffix.lower() == '.pdf':
            if not sample.startswith(b'%PDF-'):
                raise HTTPException(422, 'File không có định dạng PDF hợp lệ.')
        else:
            try:
                codecs.getincrementaldecoder('utf-8')().decode(sample, final=size <= 4096)
            except UnicodeDecodeError:
                raise HTTPException(422, 'File text phải sử dụng UTF-8.') from None
            if b'\x00' in sample:
                raise HTTPException(422, 'File text chứa dữ liệu nhị phân.')
        return head

    def finalize(self, staging_key, final_key, etag):
        # Signed PUT remains reusable until expiry: copy to an unsigned key so
        # later PUTs to staging cannot change the completed document.
        self.call('copy_object', Key=final_key,
                  CopySource={'Bucket': self.bucket, 'Key': staging_key}, CopySourceIfMatch=etag)
