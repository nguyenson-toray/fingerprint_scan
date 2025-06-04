"""
Module cấu hình logging cho ứng dụng
"""

import logging
import os
from datetime import datetime
from config import LOG_CONFIG, DATA_PATHS

def setup_logger():
    """Thiết lập logger cho ứng dụng"""
    # Tạo thư mục logs nếu chưa tồn tại
    os.makedirs(DATA_PATHS["logs"], exist_ok=True)
    
    # Tạo tên file log theo ngày
    log_filename = f"fingerprint_app_{datetime.now().strftime('%Y%m%d')}.log"
    log_path = os.path.join(DATA_PATHS["logs"], log_filename)
    
    # Cấu hình logger
    logging.basicConfig(
        level=getattr(logging, LOG_CONFIG["log_level"]),
        format=LOG_CONFIG["log_format"],
        datefmt=LOG_CONFIG["date_format"],
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Logger đã được khởi tạo")
    
    return logger