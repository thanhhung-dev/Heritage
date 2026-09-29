import pytest

class KnowledgeFactory:
    """Factory chuẩn hóa việc tạo dữ liệu tri thức mẫu cố định phục vụ kiểm thử."""
    
    @staticmethod
    def create_document(doc_id="doc_her_72", title="Di sản văn hóa miền Trung", content="Nội dung tri thức xác định phục vụ kiểm thử hệ thống."):
        return {
            "id": doc_id,
            "title": title,
            "content": content,
            "source": "heritage_knowledge_base"
        }

@pytest.fixture
def sample_knowledge_document():
    """Fixture cung cấp một bản ghi tri thức mẫu cố định."""
    return KnowledgeFactory.create_document()