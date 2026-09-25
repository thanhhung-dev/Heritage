---
title: 'Sửa lỗi Jenkins sandbox khi nạp biến kế hoạch phát hành'
type: 'bugfix'
created: '2026-09-25'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Jenkins từ chối phép gán biến môi trường động `env[p[0]] = p[1]` vì `DefaultGroovyMethods.putAt` không được Groovy Sandbox cho phép.

**Approach:** Dùng các thuộc tính `env` có tên tĩnh đã có trong Jenkinsfile và thêm kiểm tra hồi quy để cách gán động bị cấm không quay lại.

</frozen-after-approval>

## Implementation Notes

- Log lỗi trỏ đúng vào dòng 21 của revision trước `9ef065f`, nơi còn dùng `env[p[0]] = p[1]`; HEAD hiện tại đã thay bằng các phép gán thuộc tính tĩnh.
- Bổ sung kiểm tra hồi quy trong `jenkins/tests/run.sh`: xác nhận các phép gán tĩnh cần thiết tồn tại và không cho phép mẫu `env[...] =` quay lại.
- Sau review, mở rộng kiểm tra cho đủ mười biến cùng offset tương ứng và nhận diện cả khoảng trắng giữa `env` với dấu `[`.

## Review Triage Log

- `medium` — kiểm tra ban đầu chỉ bao phủ hai trong mười phép gán nên có thể bỏ sót tên biến hoặc offset sai; đã kiểm tra chính xác cả mười phép gán.
- `low` — biểu thức ban đầu không nhận diện `env [key] = value`; đã cho phép khoảng trắng tùy ý trước dấu `[`.
