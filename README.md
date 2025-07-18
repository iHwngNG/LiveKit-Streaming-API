# LiveKit Streaming API

![Python](https://img.shields.io/badge/python-3.8+-blue.svg) ![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688.svg) ![LiveKit](https://img.shields.io/badge/LiveKit-1.5+-orange.svg)

---

## 🚀 Bắt đầu

### Chuẩn bị

1.  **Python 3.8+:** Đảm bảo bạn đã cài đặt Python.
2.  **LiveKit Server:** Bạn cần có một LiveKit server đang hoạt động.
    -   **Cloud:** Đăng ký tài khoản tại [LiveKit Cloud](https://cloud.livekit.io/)

### Cài đặt

1.  **Clone repository này về máy:**
    ```bash
    git clone <URL-repository-cua-ban>
    cd <ten-thu-muc-repo>
    ```

2.  **Tạo môi trường ảo (khuyến khích):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Trên Windows: venv\Scripts\activate
    ```

3.  **Cài đặt các thư viện cần thiết:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Cấu hình môi trường:**
    Tạo một file `.env` trong thư mục gốc của dự án và điền thông tin LiveKit của bạn vào:
    ```env
    LIVEKIT_URL="<URL của LiveKit server>"  # Ví dụ: http://localhost:7880 hoặc wss://<project>.livekit.cloud
    LIVEKIT_API_KEY="<API Key của bạn>"
    LIVEKIT_API_SECRET="<API Secret của bạn>"
    ```

### Chạy ứng dụng

Mở Terminal và chạy lệnh sau từ thư mục gốc của dự án:
```bash
uvicorn main:app --reload
```

## Tóm tắt chức năng các API (http://127.0.0.1:8000/docs)

| Endpoint | Chức năng chính |
| :--- | :--- |
| `POST /rooms/create` | 🚪 Tạo một phòng stream mới với các tùy chọn như tên, số người tối đa. |
| `POST /rooms/{room_name}/join` | 🔑 **Quan trọng nhất:** Cấp "vé" (Access Token) cho người dùng để tham gia vào một phòng với vai trò Host hoặc Viewer. |
| `GET /rooms` | 📋 Liệt kê tất cả các phòng đang hoạt động trên server. |
| `GET /rooms/{room_name}` | ℹ️ Lấy thông tin chi tiết của một phòng cụ thể, bao gồm cả danh sách người tham gia. |
| `DELETE /rooms/{room_name}` | ❌ Xóa một phòng và ngắt kết nối tất cả mọi người bên trong. |
| `POST .../kick` | 👢 Đuổi một người dùng cụ thể ra khỏi phòng dựa vào `identity` của họ. |
| `ws /ws/rooms/{room_name}` | ⚡ Cung cấp kênh kết nối WebSocket để nhận các cập nhật về phòng trong thời gian thực (real-time). |
| `GET /` | ❤️‍🩹 Kiểm tra "sức khỏe" của API để xem nó có đang hoạt động hay không. |