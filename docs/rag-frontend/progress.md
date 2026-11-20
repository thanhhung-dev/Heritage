# Tiến độ Document Library theo Figma

Mốc bắt đầu: `99efb23`. Nhánh: `feature/rag-document-library-fe-r2`. Commit từng phần nhỏ theo nhịp x3; chỉ đánh dấu hoàn thành tích hợp khi hành vi API được kiểm thử.

| Giai đoạn | Nội dung | Trạng thái | Commit |
|---|---|---|---|
| P1 | Rà soát repository | DONE | `d28d0b8` |
| P2 | Phân tích Figma | DONE | `020d018`, `88ef5c0` |
| P3 | Kiểm tra contract API | DONE | `adb4280`, `5e90731`, `d299f61`, `020d018` |
| P4 | UI Document Library | DONE | `de627e9`, `250ff35`, `9448f5b`, `e2d621f` |
| P5 | Danh sách thư mục R2 | DONE | `766d95a`, `fe9d3f8`, `e2d621f` |
| P6 | Modal và trang upload | DONE | `0fd8cbc` |
| P7 | Upload thật qua URL có chữ ký | DONE | `cde439a`, `73d155c`, `8ebf649`, `742b7ba`, `c7d9e05`, `0fd8cbc` |
| P8 | Thao tác tài liệu | DONE | `9582b73`, `ae6d25a` |
| P9 | Metadata và khả năng RAG thực tế | DONE | `b22bcdf` |
| P10 | Kiểm thử | DONE | `d299f61`, `8ebf649`, `c7d9e05`, `ae6d25a`, `e07cbc7` |
| P11 | Tài liệu và nghiệm thu | DONE | Commit tài liệu cuối |

Không chạy thao tác ghi/xóa trên dữ liệu R2 production. Thiếu API nâng cao được mô tả rõ, không dùng dữ liệu mẫu Figma làm dữ liệu sản phẩm.

## Rà soát lại ngày 21/11/2026

Đã hoàn tất audit trong phạm vi Knowledge Library FE/BE, sửa lỗi tìm được và kiểm tra lại giao diện. Những mục review/ingestion thiếu API vẫn là phụ thuộc chưa hoàn tất, không được đánh dấu là workflow production hoạt động.

- BE: 31 test storage/API/contract và 5 test PostgreSQL đạt; đã sửa lộ staging khi đổi prefix.
- FE: 23 test Knowledge đạt bằng runner chuẩn; typecheck và lint phạm vi sửa đạt.
- Production build trên bản sao riêng đạt, tạo 24 trang static. Còn 2 warning ảnh có sẵn ở trang tour và khuyến nghị optional sharp.
- Browser: XHR upload, folder picker/create, exact-key delete, preview an toàn, 6 trang desktop/mobile, modal mobile và rỗng/503/401/403 đều đạt; 19 ảnh trong `.catalog-test-runtime/rag-figma/acceptance/`.
- Sửa theme kế thừa, SVG logo, nhóm nút/cột Figma, modal mobile; chặn dữ liệu cũ khi đổi key/tài khoản; giới hạn upload theo tập file được chọn; không suy đoán trạng thái review/ingestion.
- Các commit tiếp tục từ `e448fe1`: `0f9926c`, `5e79a98`, `967f113`, `7c1f941`, `5998e70`, `d8129cd`, `64b36ac`, `9e6e62e`, `4cfa60a`, `9c34243`, `b5e1d39`.

Chi tiết kết quả và giới hạn tại [final-report.md](final-report.md); nghiệm thu bằng [manual-test-vi.md](manual-test-vi.md); chạy lại fixture ở [browser README](../../apps/frontend/tests/browser/README.md).
