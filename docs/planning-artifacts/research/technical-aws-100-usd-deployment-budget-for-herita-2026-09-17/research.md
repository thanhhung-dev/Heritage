---
title: 'Chốt ngân sách AWS $100 cho HeritageGraph'
type: technical
topic: 'AWS $100 deployment budget for HeritageGraph'
decision: 'Chọn hạ tầng triển khai đồ án trong giới hạn credit AWS $100'
source: 'AWS official pricing and documentation'
status: complete
preset: standard
validation: normal
created: '2026-09-17'
updated: '2026-09-17'
verified_claims: 3
unverified_claims: 1
overturned_claims: 1
---

# Chốt ngân sách AWS $100 cho HeritageGraph

## Kết luận

**Chọn EC2 `g4dn.xlarge` On-Demand và chỉ bật khi rehearsal/demo.** Frontend ở Vercel, mô hình 3D ở Cloudflare R2. AWS chỉ giữ FastAPI + llama.cpp/Qwen trên một EC2 và lưu audio/transcript trên S3. Audio được sinh trước bằng dịch vụ Text-to-AI bên ngoài rồi upload riêng, không có TTS trong runtime.

Đây là phương án duy nhất vừa giữ được custom Qwen + LoRA, vừa có GPU để bảo vệ độ trễ demo, vừa cho phép dừng compute hoàn toàn khi không dùng. Không chọn Lightsail, Fargate, EKS, Istio, RDS hay NAT Gateway.

## Kiến trúc chốt

```diagram
┌──────────────────────┐
│ Vercel               │
│ Next.js frontend     │
└──────────┬───────────┘
           │ HTTPS
           ▼
┌──────────────────────────────────────┐
│ AWS EC2 g4dn.xlarge — On-Demand     │
│ FastAPI + NetworkX/BM25 + llama.cpp │
│ Qwen2.5-3B GGUF + LoRA              │
└──────────────────────────────────────┘

┌──────────────────────┐  ┌──────────────────────────┐
│ Cloudflare R2        │  │ Amazon S3 + CloudFront   │
│ 3D .glb              │  │ audio + transcript       │
└──────────────────────┘  └──────────────────────────┘
                              ▲
                    External Text-to-AI
                    kiểm tra rồi upload riêng
```

Jenkins chạy local hoặc chỉ bật theo phiên; không dựng một Jenkins server AWS 24/7. Docker Compose vẫn là đơn vị deploy. PostgreSQL/pgvector chỉ thêm khi tính năng dữ liệu thực sự cần; bản demo hiện tại tiếp tục dùng index RAM.

## So sánh phương án compute

Trọng số: độ trễ LLM 35%, kiểm soát chi phí 25%, đơn giản 20%, ổn định demo 20%.

| Phương án | Giá tham chiếu | Điểm / 5 | Kết luận |
|---|---:|---:|---|
| **EC2 g4dn.xlarge** | $0.526/giờ [1] | **4.35** | Chọn; GPU T4, bật/tắt theo giờ |
| EC2 m7g.large | $0.0816/giờ, ~$59.57/tháng liên tục [1] | 3.15 | Runner-up nếu benchmark CPU đạt NFR |
| Lightsail 8 GB | $44/tháng tối đa [3] | 2.80 | Dễ nhưng CPU burst và vẫn tính tiền khi stopped [4] |
| ECS/Fargate 2 vCPU/8 GB | ~$68–85/tháng liên tục [5] | 2.65 | Đắt và thừa orchestration |

`g4dn.xlarge` có 16 GiB RAM và NVIDIA T4, phù hợp inference [2]. $100 tương đương khoảng 190 giờ compute thuần, nhưng phải giữ ngân sách cho EBS, IPv4 và sai số.

## Ngân sách nên khóa

| Hạng mục | Giới hạn đề xuất |
|---|---:|
| g4dn.xlarge, tối đa **100 giờ** | $52.60 |
| EBS gp3 30 GB trong khoảng 3 tháng | ~$7–8 |
| Public/Elastic IPv4 chỉ giữ trong tháng bảo vệ | ~$3.65 [6] |
| S3, CloudFront, request/log nhỏ | ≤$5 |
| **Dự phòng không được tiêu** | **≥$30** |

Không dùng GPU hàng ngày. Development và evaluation chạy trên Mac/MLX. EC2 chỉ dùng cho integration test cuối, rehearsal và ngày bảo vệ.

## Lịch sử dụng credit

1. **Ngay bây giờ — $0–5:** kiểm tra ngày hết hạn và dịch vụ được credit bao phủ trong Billing → Credits. Tạo Budgets tại $5, $10 forecast, $25, $50 và CloudWatch alarms; cảnh báo có độ trễ, không phải hard cap [10][11].
2. **Giai đoạn phát triển — ≤$10:** làm local. Chỉ tạo S3 private, sinh một audio mẫu và kiểm tra Docker image.
3. **Trước bảo vệ 3–4 tuần — tổng ≤$25:** xin quota G instance, chạy g4dn 10–20 giờ để benchmark, sửa CUDA/llama.cpp và đo p95.
4. **Hai tuần cuối — tổng ≤$55:** rehearsal 2–4 giờ/lần; dừng instance ngay sau buổi test. EC2 stopped không tính compute nhưng EBS vẫn tồn tại [7].
5. **Ngày bảo vệ — tổng trần $70:** khởi động trước 60–90 phút, health check, warm model và giữ nguyên On-Demand. Không dùng Spot cho endpoint duy nhất.
6. **Sau bảo vệ:** terminate instance, xóa EBS/snapshot thừa, release Elastic IP và kiểm tra Bills thêm 48 giờ.

## Audio và media

- **Sinh audio:** dùng Text-to-AI bên ngoài, xuất file trước khi deploy; không gọi TTS khi người dùng bấm phát.
- **Upload riêng:** kiểm tra transcript/bằng chứng, sau đó upload MP3 + transcript lên S3 theo version/hash.
- **Lưu trữ:** S3 private, Block Public Access; phân phối bằng CloudFront [15]. Chi phí storage/request theo S3 [14].
- **3D:** tiếp tục Cloudflare R2, không nhân đôi sang S3.

## Rủi ro và điều kiện chuyển phương án

- Free Plan mới có $100 credit và tối đa 6 tháng; một số dịch vụ có thể bị giới hạn. Nếu g4dn không khả dụng, nâng lên Paid Plan trong 6 tháng vẫn giữ quyền dùng Free Tier credits, nhưng phần vượt credit sẽ tính vào thẻ [12][13]. Kiểm tra điều khoản tài khoản trước khi nâng.
- GPU quota có thể bằng 0. Xin quota sớm, không chờ tuần bảo vệ.
- Nếu benchmark `m7g.large` đáp ứng p95 ≤8 giây, chuyển sang CPU để có nhiều giờ online hơn. Nếu không, giữ g4dn.
- Lightsail chỉ là fallback đơn giản; stopped vẫn bị tính phí cho tới khi xóa [4].
- Text-to-AI là bước offline; nếu dịch vụ này lỗi, các audio đã upload vẫn phát bình thường.

## Nguồn

| Ref | Nguồn | Hỗ trợ |
|---|---|---|
| [1] | [AWS EC2 Price List API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.json), accessed 2026-09-17 | Giá EC2 us-east-1 |
| [2] | [AWS G4 instances](https://aws.amazon.com/ec2/instance-types/g4/), accessed 2026-09-17 | T4, RAM và use case inference |
| [3] | [Lightsail bundles](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html), accessed 2026-09-17 | Cấu hình/giá bundle |
| [4] | [Lightsail billing FAQ](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-frequently-asked-questions-faq-billing-and-account-management.html), accessed 2026-09-17 | Stopped vẫn tính phí |
| [5] | [Fargate pricing](https://aws.amazon.com/fargate/pricing/), accessed 2026-09-17 | Giá vCPU/RAM |
| [6] | [Amazon VPC pricing](https://aws.amazon.com/vpc/pricing/), accessed 2026-09-17 | IPv4 $0.005/giờ |
| [7] | [EC2 stop/start](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html), accessed 2026-09-17 | Lifecycle stopped/EBS |
| [10] | [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html), accessed 2026-09-17 | Cảnh báo actual/forecast và độ trễ |
| [11] | [CloudWatch billing alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/monitor_estimated_charges_with_cloudwatch.html), accessed 2026-09-17 | Billing alarm |
| [12] | [AWS Free Tier](https://aws.amazon.com/free/), accessed 2026-09-17 | $100 ban đầu, tối đa 6 tháng |
| [13] | [AWS Free Tier FAQ](https://aws.amazon.com/free/free-tier-faqs/), accessed 2026-09-17 | Credit khi chọn/nâng Paid Plan |
| [14] | [S3 pricing](https://aws.amazon.com/s3/pricing), accessed 2026-09-17 | Storage/request/transfer |
| [15] | [S3 website access permissions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteAccessPermissionsReqd.html), accessed 2026-09-17 | Block Public Access và CloudFront thay cho public bucket |

## Staleness

Kiểm tra lại giá EC2, credit balance/expiry và GPU quota **7 ngày trước khi provisioning**, rồi kiểm tra lại Billing mỗi ngày trong tuần bảo vệ. Giá và Free Tier terms là các dữ kiện hết hạn nhanh nhất.
