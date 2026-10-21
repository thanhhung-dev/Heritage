# Jenkins local agent

Image này là build agent cho pipeline Heritage. Jenkins Controller vẫn chạy riêng; agent nhận job qua inbound connection và dùng Docker socket của máy host để thực hiện Docker/Compose checks.

## Build image

Chạy từ repository root:

```bash
docker build -f docker/jenkins-agent/Dockerfile -t heritage-jenkins-agent:local .
```

Kiểm tra toolchain:

```bash
docker run --rm heritage-jenkins-agent:local bash -lc '
  python3 --version
  node --version
  npm --version
  docker --version
  docker compose version
  terraform version
  aws --version
  git --version
'
```

## Kết nối vào Jenkins Controller

Trong Jenkins UI:

1. Vào `Manage Jenkins` → `Nodes` → `New Node`.
2. Đặt tên `heritage-local-agent`.
3. Chọn `Permanent Agent`.
4. Đặt label `heritage-linux`.
5. Chọn `Launch agents via inbound connection`.
6. Lưu và mở trang node để lấy lệnh `docker run` có sẵn `-url`, `-secret` và `-name`.

Chỉnh lệnh Jenkins sinh ra để mount Docker socket và workspace:

```bash
docker run -d \
  --name heritage-local-agent \
  --restart unless-stopped \
  --group-add 0 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v heritage_agent_workdir:/home/jenkins/agent \
  heritage-jenkins-agent:local \
  -url http://host.docker.internal:8080/ \
  -secret '<SECRET_FROM_JENKINS>' \
  -name heritage-local-agent \
  -workDir /home/jenkins/agent
```

`--group-add 0` cho phép user `jenkins` truy cập Docker Desktop socket, thường được mount dưới dạng `root:root` với mode `660`. Trên Linux, dùng GID thật của socket thay cho `0`:

```bash
--group-add "$(stat -c '%g' /var/run/docker.sock)"
```

Trên Linux, thay `host.docker.internal` bằng địa chỉ host mà container truy cập được, hoặc thêm:

```bash
--add-host host.docker.internal:host-gateway
```

Nếu Jenkins Controller cũng chạy trong Docker, dùng tên container/controller trên cùng Docker network thay cho `host.docker.internal`.

## Jenkinsfile agent label

Để pipeline sử dụng agent này, đổi Jenkinsfile root thành:

```groovy
agent { label 'heritage-linux' }
```

Không cần đổi label nếu job đã cấu hình node restriction tương ứng.

## Giới hạn local

Mount `/var/run/docker.sock` cấp cho agent quyền điều khiển Docker daemon của máy host. Chỉ dùng agent này cho Jenkins local đáng tin cậy; không dùng chung với job hoặc PR không đáng tin cậy. AWS credentials chưa cần bind khi chỉ chạy quality gates local.
