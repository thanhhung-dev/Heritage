# Hướng dẫn test tay Document Library

Ngày cập nhật: 21/11/2026. UI dùng tiếng Anh. Các bước này áp dụng cho nhánh `feature/rag-document-library-fe-r2`.

## Chuẩn bị môi trường

Chạy frontend và backend theo cấu hình của dự án. Cần tài khoản Admin hợp lệ, private JWT secret, kết nối database, migration Knowledge Library đã được triển khai và cấu hình R2 cho bucket `knowledge-heritage`. Nếu upload báo lỗi CORS, kiểm tra cả origin backend và CORS bucket cho PUT cùng các signed header.

Dùng môi trường kiểm thử và folder riêng, ví dụ `manual-test-20261121/`, vì tạo folder, upload và xác nhận xóa thực sự thay đổi dữ liệu. Có thể dùng [browser fixture](../../apps/frontend/tests/browser/README.md) để thử giao diện hoàn toàn cục bộ, không đụng R2 thật.

Tạo 3 file UTF-8 nhỏ: `sample.md`, `sample.txt`, `sample.json` với JSON hợp lệ. Chuẩn bị thêm file `.pdf` và JSON sai cú pháp để thử từ chối.

## 1. Giao diện và điều hướng

1. Đăng nhập Admin rồi mở `/admin/documents`.
2. Ở màn hình rộng 1920×1200, kiểm tra sidebar sáng rộng 260px, logo đủ màu, panel trắng bo góc, chữ/nút rõ. Library có hai nút chính **Create folder**, **Upload documents**.
3. Chọn folder, bấm breadcrumb, dùng Back/Forward. Folder và URL `?prefix=` phải khớp, không hiển thị dữ liệu của folder cũ trong lúc chuyển.
4. Gõ tìm tên file. Kết quả chỉ lọc các file đã tải; nếu còn dữ liệu, dùng **Load more**. Không coi số đã tải là tổng số toàn bucket.
5. Thu màn hình về 390px. Sidebar thu gọn; nội dung đọc được, bảng cuộn ngang bên trong và toàn trang không tràn ngang. Bấm biểu tượng tìm kiếm trên sidebar mở/focus ô tìm file.

## 2. Tạo folder

1. Bấm **Create folder**, nhập tên folder thử nghiệm rồi xác nhận.
2. Folder mới phải xuất hiện sau khi danh sách làm mới.
3. Thử tên rỗng hoặc tên không hợp lệ: có thông báo lỗi, không báo thành công giả. Đóng/mở lại dialog không giữ lỗi cũ.

## 3. Upload trong modal

1. Mở folder thử nghiệm, bấm **Upload documents**. Modal nền trắng, có đích lưu, dropzone, danh sách tệp và footer.
2. Bấm **Change folder**, chọn một folder khác. Đường dẫn đích phải đổi. File chọn sau đó thuộc đích này.
3. Chọn ba file hợp lệ; thử thêm PDF để kiểm tra thông báo từ chối. Gỡ một file bằng nút ×.
4. Bấm **Upload N files**. Theo dõi Preparing → Uploading → Verifying upload → Stored in R2.
5. 100% byte đã truyền chưa đủ để kết luận Stored. Chỉ sau phản hồi complete thành công mới có Stored và key tương ứng.
6. Mở lại folder đích trong thư viện: file phải tồn tại với tên/dung lượng đúng. Các file đang chờ trong folder khác không được tự chạy khi bấm upload của modal hiện tại.

## 4. Trang upload và phục hồi

1. Bấm **Open full upload page**. Chọn folder ở cây bên trái hoặc bấm **Change destination** để chuyển focus về cây; trang vẫn ở workspace upload.
2. Chọn vài file. **Start upload** của một hàng chỉ bắt đầu file đó; **Upload N queued files** bắt đầu toàn bộ hàng đợi đang hiển thị.
3. Modal và workspace dùng chung hàng đợi khi điều hướng bằng link trong ứng dụng. Reload trang sẽ bỏ hàng đợi trong bộ nhớ.
4. Dùng Network throttling của DevTools để thấy tiến độ thực. Thử **Cancel upload** khi đang gửi; file chuyển Cancelled và các file khác vẫn xử lý được.
5. Thử ngắt mạng rồi **Retry upload**. Retry kiểm tra complete của cùng upload ID trước; không tự ghi đè object đã tồn tại.
6. Upload lại cùng tên trong cùng folder phải báo conflict. URL PUT hết hạn nhưng phiên còn giữ chỗ có thể yêu cầu chờ phiên hết hạn; không đổi tên hay bỏ điều kiện chống ghi đè tự động.

## 5. Chi tiết, tải xuống và xóa

1. Bấm **View** hoặc tên file. Kiểm tra tên, key, dung lượng, MIME/format và thời gian thật; Storage là Stored in R2. Review/Ingestion hiển thị Unavailable khi API chưa có dữ liệu.
2. Với Markdown chứa `<script>alert(1)</script>`, preview chỉ hiện văn bản, không thực thi. File quá lớn cho preview phải có lỗi rõ và vẫn có lựa chọn tải xuống.
3. Bấm **View original** hoặc **Download file**; mở/tải qua URL ký ngắn hạn. Trong Network, request PUT/download đến R2 không mang bearer JWT của ứng dụng.
4. Chuyển nhanh giữa hai URL details/metadata với key khác nhau: không giữ nội dung, preview hay dialog xác nhận của file trước.
5. Ở thẻ **Metadata and original file**, bấm **Delete file**. Xem đúng tên và exact key trước khi xác nhận. Chỉ file thử nghiệm này bị xóa và danh sách thư mục cha được cập nhật.

## 6. Những phần hiện chưa khả dụng

Metadata biên tập, Save draft, Submit for review, Approve, Replace và Run/Retry ingestion đang bị khóa do chưa có contract production phù hợp. Trang vẫn cho xem thông tin file gốc. Không kỳ vọng upload tự đưa nội dung vào chatbot, không coi Unavailable là đã duyệt/chưa chạy/đã index.

## 7. Quyền và lỗi

1. Xóa phiên đăng nhập rồi mở thư viện: phải yêu cầu Sign in; không lộ danh sách cũ.
2. Dùng tài khoản không phải Admin: phải báo thiếu quyền; backend vẫn quyết định quyền thực tế.
3. Đổi giữa hai tài khoản: cache và hàng đợi của tài khoản trước phải bị ẩn ngay.
4. Tạm dừng API trong môi trường test: có thông báo lỗi và **Try again**; khởi động lại rồi thử lại, không để spinner vô hạn.
5. Folder rỗng hiển thị trạng thái rỗng rõ ràng. JSON sai nội dung có thể bị backend từ chối ở bước xác minh; UI không được đánh dấu Stored.

Sau khi thử trên R2 test, chỉ dọn các file do bạn tạo trong folder thử nghiệm. Báo lỗi kèm route, exact key, status HTTP và ảnh màn hình; không gửi token hay signed URL còn hiệu lực.
