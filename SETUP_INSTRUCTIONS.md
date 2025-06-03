# Hướng dẫn Setup Ứng dụng Quản lý Vân tay

## Yêu cầu hệ thống

### Phần cứng
- Máy quét vân tay ZKTeco SLK20R (hoặc tương thích)
- Máy chấm công ZKTeco F21lite
- Kết nối USB cho máy quét vân tay
- Kết nối mạng LAN cho máy chấm công

### Phần mềm
- Windows 10/11 (64-bit)
- Python 3.8 hoặc cao hơn
- ZKTeco SDK

## Cài đặt

### 1. Cài đặt Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Cài đặt ZKTeco SDK và libzkfp.dll

#### Tải về SDK
- Tải ZKTeco Standalone SDK từ trang chủ ZKTeco
- Giải nén và tìm file `libzkfp.dll` trong thư mục SDK

#### Cài đặt DLL
Có 3 cách để cài đặt `libzkfp.dll`:

**Cách 1: Copy vào thư mục dự án (Khuyến nghị)**
```
project_folder/
├── libzkfp.dll
├── main.py
├── fingerprint_scanner.py
└── ...
```

**Cách 2: Copy vào System32**
- Copy `libzkfp.dll` vào `C:\Windows\System32\`
- Yêu cầu quyền Administrator

**Cách 3: Copy vào thư mục Python**
- Copy `libzkfp.dll` vào thư mục cài đặt Python (ví dụ: `C:\Python39\`)

### 3. Cấu hình thiết bị

#### Máy quét vân tay SLK20R
- Kết nối USB với máy tính
- Cài đặt driver nếu cần thiết
- Kiểm tra Device Manager để đảm bảo thiết bị được nhận dạng

#### Máy chấm công F21lite
- Kết nối mạng LAN
- Cấu hình IP address trong file `config.py`:
```python
ATTENDANCE_DEVICES = [
    {
        "id": 1,
        "name": "Máy chấm công 1",
        "ip": "10.0.1.48",  # Thay đổi IP này
        "port": 4370,
        # ...
    }
]
```

### 4. Cấu hình ERPNext

#### API Keys
Cập nhật thông tin API trong file `config.py`:
```python
ERPNEXT_CONFIG = {
    "url": "http://your-erpnext-server",  # Thay đổi URL
    "api_key": "your-api-key",           # Thay đổi API key
    "api_secret": "your-api-secret"      # Thay đổi API secret
}
```

#### Tạo API Key trong ERPNext
1. Đăng nhập ERPNext với quyền Administrator
2. Vào Settings > Integrations > API Key
3. Tạo API Key mới cho user có quyền truy cập Employee doctype
4. Copy API Key và API Secret vào config

## Chạy ứng dụng

### Khởi động ứng dụng
```bash
python main.py
```

### Quy trình sử dụng
1. **Kết nối thiết bị**
   - Click "Kết nối Scanner" để kết nối máy quét vân tay
   - Click "Kết nối ERPNext" để kết nối với hệ thống HRMS

2. **Chọn nhân viên**
   - Danh sách nhân viên sẽ tự động tải từ ERPNext
   - Sử dụng ô tìm kiếm để lọc nhân viên
   - Click chọn nhân viên cần thêm vân tay

3. **Quét vân tay**
   - Chọn ngón tay cần quét (0-9)
   - Click "Thêm vân tay"
   - Đặt ngón tay lên máy quét 3 lần theo hướng dẫn

4. **Lưu dữ liệu**
   - Click "Lưu vân tay cục bộ" để lưu vào file JSON
   - Dữ liệu được lưu trong thư mục `data/all_fingerprints.json`

5. **Gán ID máy chấm công**
   - Click "Gán ID máy CC tự động" để tự động gán ID cho nhân viên chưa có
   - ID sẽ được đồng bộ lên ERPNext

6. **Đồng bộ máy chấm công**
   - Chọn thiết bị cần đồng bộ (hoặc "Tất cả thiết bị")
   - Click "Đồng bộ" để gửi dữ liệu vân tay lên máy chấm công

## Cấu trúc thư mục dữ liệu

```
project_folder/
├── data/
│   └── all_fingerprints.json    # Dữ liệu vân tay cục bộ
├── log/
│   └── fingerprint_app_*.log    # File log theo ngày
├── photos/
│   └── logo.png                 # Logo ứng dụng (tùy chọn)
└── ...
```

## Xử lý sự cố

### Lỗi kết nối máy quét vân tay
- Kiểm tra kết nối USB
- Đảm bảo `libzkfp.dll` đã được copy đúng vị trí
- Kiểm tra Device Manager xem thiết bị có được nhận dạng

### Lỗi kết nối máy chấm công
- Kiểm tra kết nối mạng
- Ping IP address của máy chấm công
- Kiểm tra firewall có block port 4370

### Lỗi API ERPNext
- Kiểm tra URL, API Key, API Secret
- Đảm bảo user có quyền truy cập Employee doctype
- Kiểm tra kết nối mạng đến ERPNext server

### Lỗi quét vân tay
- Đảm bảo ngón tay sạch và khô
- Đặt ngón tay đúng vị trí trên cảm biến
- Thử quét lại nếu chất lượng vân tay kém

## Ghi chú kỹ thuật

### Định dạng template vân tay
- Template được lưu dưới dạng base64 string
- Kích thước mặc định: 512 bytes (có thể thay đổi trong config)
- Được merge từ 3 lần quét để tăng độ chính xác

### Bảo mật dữ liệu
- Template vân tay được mã hóa base64
- Dữ liệu chỉ lưu cục bộ, không gửi template lên ERPNext
- Log file ghi lại tất cả hoạt động để audit

### Performance
- Ứng dụng sử dụng background threads để tránh đóng băng UI
- Kết nối thiết bị được quản lý tự động (mở/đóng)
- Dữ liệu được cache trong memory để tăng tốc độ truy cập