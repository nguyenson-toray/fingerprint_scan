"""
Cấu hình hệ thống ban đầu cho ứng dụng quản lý vân tay.
Các cấu hình này có thể được ghi đè bởi dữ liệu từ ERPNext sau khi kết nối.
"""

# Thông tin ứng dụng
APP_INFO = {
    "title": "PHẦN MỀM QUẢN LÝ VÂN TAY, MÁY CHẤM CÔNG - ĐỒNG BỘ VỚI HỆ THỐNG ERPNEXT, HRMS",
    "version": "1.0.0",
    "subtitle": "Phát triển bởi nhóm IT - TIQN",
    "title_version": "PHẦN MỀM QUẢN LÝ VÂN TAY, MÁY CHẤM CÔNG - Version 1.0.0"
}

# Cấu hình ERPNext API
ERPNEXT_CONFIG = {
    "url": 'http://10.0.1.21',
    "api_key": "5ce1b64f62ada3e",
    "api_secret": "fa4742cd637e071"
}

# Danh sách máy chấm công ZKTeco F21lite (sẽ được ghi đè từ ERPNext)
ATTENDANCE_DEVICES = [
    {
        "id": 1,
        "device_name": "Máy chấm công 1",
        "ip_address": "10.0.1.48",
        "port": 4370,
        "password": "",
        "model": "ZKTeco F21lite",
        "location": "Hành lang văn phòng",
        "timeout": 10,
        "force_udp": True,
        "ommit_ping": True,
        "sync_interval": 300,
        "enable": True
    }
]

# Cấu hình scanner vân tay
SCANNER_CONFIG = {
    "model": "ZKTeco SLK20R",
    "connection": "USB",
    "timeout": 30
}

# Cấu hình logging
LOG_CONFIG = {
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S"
}

# Cấu hình giao diện
UI_CONFIG = {
    "app_title": f"Phần mềm quản lý vân tay nhân viên - Đồng bộ máy chấm công & ERPNext, HRMS v{APP_INFO['version']} - Phát triển bởi nhóm IT - TIQN",
    "window_width": 1400,
    "window_height": 800,
    "theme": "blue",
    "appearance_mode": "dark"  # Có thể chuyển sang "dark" hoặc "light"
}

# Mapping ngón tay
FINGER_MAPPING = {
    0: "Ngón cái trái",
    1: "Ngón trỏ trái", 
    2: "Ngón giữa trái",
    3: "Ngón áp út trái",
    4: "Ngón út trái",
    5: "Ngón cái phải",
    6: "Ngón trỏ phải",
    7: "Ngón giữa phải",
    8: "Ngón áp út phải",
    9: "Ngón út phải"
}

# Cấu hình vân tay
FINGERPRINT_CONFIG = {
    "quality_threshold": 70,
    "scan_count": 3,
    "template_size": 512,
    "template_format": "base64"
}

# Cấu hình đồng bộ
SYNC_CONFIG = {
    "retry_count": 3,
    "retry_delay": 5,
    "batch_size": 10,
    "timeout": 30
}

# Đường dẫn file dữ liệu
DATA_PATHS = {
    "fingerprints": "data/all_fingerprints.json",
    "devices": "data/attendance_devices.json",
    "logs": "logs/"
}