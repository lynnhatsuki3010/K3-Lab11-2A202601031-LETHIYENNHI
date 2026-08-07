# Demo Chat Client (Attack/Defense)

Chat box để demo trực tiếp 3 phiên bản agent trong bài lab — không phải phần chấm điểm, chỉ để trực quan hoá kết quả TODO 1-14 đã làm.

- **Unsafe** — `create_unsafe_agent()`, không có guardrail nào.
- **Protected** — agent dùng đúng `InputGuardrailPlugin` + `OutputGuardrailPlugin` tự viết (`src/guardrails/`).
- **Guards** — `create_guards_agent()`, mục tiêu bonus của đề (đã có sẵn, không sửa).

Mỗi câu trả lời hiện badge: `LEAKED` (lộ secret), `BLOCKED (layer)` (bị chặn ở lớp nào), hoặc `OK`.

## Chạy

```powershell
.\.venv\Scripts\Activate.ps1
# đảm bảo .env đã có GOOGLE_API_KEY (xem README.md gốc)
cd client
uvicorn server:app --reload --port 8000
```

Mở trình duyệt: http://127.0.0.1:8000

Bấm một prompt mẫu bên trái để tự điền vào ô chat, hoặc tự gõ câu hỏi. Đổi agent bằng nút bên trái — mỗi agent giữ hội thoại riêng (nút "Reset hội thoại" để xoá phiên hiện tại).

Lưu ý: dùng chung Gemini free-tier quota (~15 request/phút) với phần chấm bài — tránh bấm gửi liên tục quá nhanh.
