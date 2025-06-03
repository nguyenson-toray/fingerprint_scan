# config.py
"""
Cấu hình hệ thống cho ứng dụng quản lý vân tay
"""

# Cấu hình ERPNext API
ERPNEXT_CONFIG = {
    "url":  'http://10.0.1.21',
    "api_key": "5ce1b64f62ada3e",
    "api_secret": "fa4742cd637e071"
}

# Danh sách máy chấm công ZKTeco F21lite
ATTENDANCE_DEVICES = [
    {
        "id": 1,
        "name": "Máy chấm công 1",
        "ip": "10.0.1.48",
        "port": 4370,
        "password": "",
        "model": "ZKTeco F21lite",
        "location": "Hành lang văn phòng",
        "timeout": 10,
        "force_udp": True,
        "ommit_ping": True,
        "sync_interval": 300  # 5 phút
    } 
]

# Cấu hình scanner vân tay
SCANNER_CONFIG = {
    "model": "ZKTeco SLK20R",
    "connection": "USB",
    "timeout": 30  # Thời gian chờ quét vân tay (giây)
}

# Cấu hình logging
LOG_CONFIG = {
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S"
}

# Cấu hình giao diện
UI_CONFIG = {
    "app_title": "Quản lý vân tay nhân viên - ERPNext HRMS",
    "window_width": 1400,
    "window_height": 800,
    "theme": "darkblue"
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
    "quality_threshold": 70,  # Ngưỡng chất lượng vân tay (0-100)
    "scan_count": 3,  # Số lần quét mỗi ngón tay
    "template_size": 512,  # Kích thước template vân tay
    "template_format": "base64"  # Định dạng lưu template
}

# Cấu hình đồng bộ
SYNC_CONFIG = {
    "retry_count": 3,  # Số lần thử lại khi đồng bộ thất bại
    "retry_delay": 5,  # Thời gian chờ giữa các lần thử (giây)
    "batch_size": 10,  # Số lượng nhân viên đồng bộ mỗi lần
    "timeout": 30  # Thời gian chờ đồng bộ (giây)
}
