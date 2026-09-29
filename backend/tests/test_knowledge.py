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

def test_deterministic_knowledge_factory():
    """Xác thực dữ liệu sinh ra từ KnowledgeFactory đúng chuẩn xác định."""
    sample_doc = KnowledgeFactory.create_document()
    
    assert sample_doc["id"] == "doc_her_72"
    assert sample_doc["source"] == "heritage_knowledge_base"
    assert sample_doc["title"] == "Di sản văn hóa miền Trung"
    
    custom_doc = KnowledgeFactory.create_document(doc_id="doc_custom_99", title="Phố cổ Hội An")
    assert custom_doc["id"] == "doc_custom_99"
    assert custom_doc["title"] == "Phố cổ Hội An"`