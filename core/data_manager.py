"""
Module quản lý dữ liệu local
"""

import json
import os
import logging
from typing import Dict, List, Any
from config import DATA_PATHS, ATTENDANCE_DEVICES

logger = logging.getLogger(__name__)

class DataManager:
    """Lớp quản lý dữ liệu local"""
    
    def __init__(self):
        # Tạo thư mục data nếu chưa tồn tại
        os.makedirs("data", exist_ok=True)
    
    def load_local_fingerprints(self) -> Dict[str, Any]:
        """Tải dữ liệu vân tay từ file local"""
        try:
            if os.path.exists(DATA_PATHS["fingerprints"]):
                with open(DATA_PATHS["fingerprints"], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Chuyển đổi từ list sang dict với key là employee
                if isinstance(data, list):
                    fingerprints_dict = {}
                    for item in data:
                        if item.get('employee'):
                            fingerprints_dict[item['employee']] = item
                    return fingerprints_dict
                else:
                    return data
            else:
                return {}
        except Exception as e:
            logger.error(f"❌ Lỗi tải dữ liệu vân tay local: {str(e)}")
            return {}
    
    def save_local_fingerprints(self, fingerprints_data: Dict[str, Any]):
        """Lưu dữ liệu vân tay vào file local"""
        try:
            # Chuyển đổi từ dict sang list để tương thích với format cũ
            data_list = list(fingerprints_data.values())
            
            with open(DATA_PATHS["fingerprints"], 'w', encoding='utf-8') as f:
                json.dump(data_list, f, ensure_ascii=False, indent=4)
            
            logger.info(f"✅ Đã lưu {len(data_list)} nhân viên vào file local")
        except Exception as e:
            logger.error(f"❌ Lỗi lưu dữ liệu vân tay local: {str(e)}")
            raise
    
    def load_device_config(self) -> List[Dict[str, Any]]:
        """Tải cấu hình máy chấm công từ file local hoặc config.py"""
        try:
            # Thử tải từ file local trước
            if os.path.exists(DATA_PATHS["devices"]):
                with open(DATA_PATHS["devices"], 'r', encoding='utf-8') as f:
                    devices = json.load(f)
                logger.info(f"✅ Đã tải {len(devices)} máy chấm công từ file local")
                return devices
            else:
                # Sử dụng cấu hình từ config.py
                logger.info(f"✅ Sử dụng {len(ATTENDANCE_DEVICES)} máy chấm công từ config.py")
                return ATTENDANCE_DEVICES.copy()
        except Exception as e:
            logger.error(f"❌ Lỗi tải cấu hình máy chấm công: {str(e)}")
            return ATTENDANCE_DEVICES.copy()
    
    def save_device_config(self, devices: List[Dict[str, Any]]):
        """Lưu cấu hình máy chấm công vào file local"""
        try:
            with open(DATA_PATHS["devices"], 'w', encoding='utf-8') as f:
                json.dump(devices, f, ensure_ascii=False, indent=4)
            
            logger.info(f"✅ Đã lưu {len(devices)} máy chấm công vào file local")
        except Exception as e:
            logger.error(f"❌ Lỗi lưu cấu hình máy chấm công: {str(e)}")
            raise