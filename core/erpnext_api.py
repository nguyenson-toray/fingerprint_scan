# erpnext_api.py
"""
Module tương tác với ERPNext HRMS API
"""

import requests
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import base64
from config import ERPNEXT_CONFIG

logger = logging.getLogger(__name__)


class ERPNextAPI:
    """Lớp xử lý tương tác với ERPNext API"""
    
    def __init__(self):
        self.base_url = ERPNEXT_CONFIG["url"]
        self.api_key = ERPNEXT_CONFIG["api_key"]
        self.api_secret = ERPNEXT_CONFIG["api_secret"]
        self.session = requests.Session()
        self.is_connected = False
        
        # Cấu hình headers
        self.session.headers.update({
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        })
    
    def test_connection(self) -> bool:
        """Kiểm tra kết nối với ERPNext"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/method/frappe.auth.get_logged_user"
            )
            
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"✅ Kết nối ERPNext thành công! User: {user_data.get('message')}")
                self.is_connected = True
                return True
            else:
                logger.error(f"❌ Lỗi kết nối ERPNext: {response.status_code}")
                self.is_connected = False
                return False
                
        except Exception as e:
            logger.error(f"❌ Không thể kết nối ERPNext: {str(e)}")
            self.is_connected = False
            return False
    
    def get_all_employees(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả nhân viên từ HRMS"""
        try:
            # Lấy danh sách employee với custom_group thay vì department
            response = self.session.get(
                f"{self.base_url}/api/resource/Employee",
                params={
                    "fields": json.dumps([
                        "name", "employee_name", "employee", 
                        "attendance_device_id", "custom_group", 
                        "designation", "status", "custom_password",
                        "custom_privilege"
                    ]),
                    "filters": json.dumps([["status", "=", "Active"]]),
                    "order_by": "employee desc",
                    "limit_page_length": 1000
                }
            )
            
            if response.status_code == 200:
                employees = response.json().get("data", [])
                logger.info(f"✅ Lấy được {len(employees)} nhân viên từ ERPNext")
                return employees
            else:
                logger.error(f"❌ Lỗi khi lấy danh sách nhân viên: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi lấy danh sách nhân viên: {str(e)}")
            return []
    
    def get_attendance_machines(self) -> List[Dict[str, Any]]:
        """
        Lấy danh sách máy chấm công từ ERPNext
        
        Returns:
            Danh sách thông tin máy chấm công
        """
        try:
            # Kiểm tra DocType Attendance Machine tồn tại trước
            check_response = self.session.get(
                f"{self.base_url}/api/resource/DocType/Attendance Machine"
            )
            
            if check_response.status_code == 404:
                logger.warning("⚠️ DocType 'Attendance Machine' không tồn tại trong ERPNext")
                logger.info("💡 Để sử dụng tính năng này, vui lòng tạo DocType 'Attendance Machine' trong ERPNext")
                return []
            
            # Lấy danh sách từ DocType Attendance Machine
            response = self.session.get(
                f"{self.base_url}/api/resource/Attendance Machine",
                params={
                    "fields": json.dumps([
                        "name", "id", "device_name", "ip_address", "port", 
                        "model", "location", "enable", "timeout", "force_udp", "ommit_ping"
                    ]),
                    "filters": json.dumps([["enable", "=", 1]]),
                    "order_by": "id"
                }
            )
            
            if response.status_code == 200:
                devices_data = response.json().get("data", [])
                
                # Convert to standard format expected by the app
                devices = []
                for device_data in devices_data:
                    # Map fields correctly từ ERPNext sang format của app
                    device = {
                        'id': device_data.get('id', 1),
                        'name': device_data.get('name', ''),  # ERPNext document name
                        'device_name': device_data.get('device_name', f'Device {device_data.get("id", 1)}'),
                        'ip': device_data.get('ip_address', ''),  # Map ip_address -> ip
                        'port': device_data.get('port', 4370),
                        'model': device_data.get('model', 'ZKTeco F21lite'),
                        'location': device_data.get('location', 'Unknown'),
                        'timeout': device_data.get('timeout', 10),
                        'force_udp': bool(device_data.get('force_udp', 1)),
                        'ommit_ping': bool(device_data.get('ommit_ping', 1)),
                        'enable': bool(device_data.get('enable', 1))
                    }
                    devices.append(device)
                
                logger.info(f"✅ Lấy được {len(devices)} máy chấm công từ ERPNext Attendance Machine")
                return devices
            else:
                logger.error(f"❌ Lỗi khi lấy danh sách máy chấm công: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi lấy danh sách máy chấm công: {str(e)}")
            return []
            
    def update_employee_attendance_device_id(self, employee_name: str, attendance_device_id: int) -> bool:
        """
        Cập nhật attendance_device_id cho nhân viên trên ERPNext.
        Args:
            employee_name: Tên của nhân viên (doc.name trong ERPNext).
            attendance_device_id: ID thiết bị chấm công mới.
        Returns:
            True nếu cập nhật thành công, False nếu thất bại.
        """
        try:
            response = self.session.put(
                f"{self.base_url}/api/resource/Employee/{employee_name}",
                json={
                    "attendance_device_id": attendance_device_id
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Cập nhật attendance_device_id cho {employee_name} thành công: {attendance_device_id}")
                return True
            else:
                logger.error(f"❌ Lỗi cập nhật attendance_device_id cho {employee_name}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi khi cập nhật attendance_device_id cho {employee_name}: {str(e)}")
            return False
    
    def update_employee_attendance(self, employee_name: str, fingerprint_data: dict) -> bool:
        """
        Lưu dữ liệu vân tay vào childtable "Fingerprint Data" của Employee

        Args:
            employee_name: Tên của nhân viên (doc.name trong ERPNext)
            fingerprint_data: Dữ liệu vân tay (chứa danh sách fingerprints)

        Returns:
            True nếu cập nhật thành công, False nếu thất bại
        """
        try:
            if not fingerprint_data or 'fingerprints' not in fingerprint_data:
                logger.warning(f"⚠️ Không có dữ liệu vân tay cho nhân viên {employee_name}")
                return False

            # Chuẩn bị dữ liệu để gửi lên ERPNext
            fingerprints = []
            for fp in fingerprint_data.get('fingerprints', []):
                fingerprints.append({
                    "doctype": "Fingerprint Data", 
                    "finger_index": fp.get('finger_index', 0),
                    "finger_name": fp.get('finger_name', ''),
                    "template_data": fp.get('template_data', ''),
                    "quality_score": fp.get('quality_score', 70)
                })
        
            # Sử dụng REST API standard thay vì custom method
            response = self.session.put(
                f"{self.base_url}/api/resource/Employee/{employee_name}",
                json={
                    "custom_fingerprints": fingerprints  # Tên của child table field
                }
            )
        
            if response.status_code == 200:
                logger.info(f"✅ Đã cập nhật {len(fingerprints)} vân tay cho {employee_name}")
                return True
            else:
                logger.error(f"❌ Lỗi cập nhật vân tay cho {employee_name}: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Lỗi khi cập nhật vân tay cho {employee_name}: {str(e)}")
            return False
    
    def log_sync_history(self, sync_type: str, device_name: str, 
                        employee_count: int, status: str, message: str = "") -> bool:
        """
        Ghi log lịch sử đồng bộ
        
        Args:
            sync_type: Loại đồng bộ (fingerprint/attendance)
            device_name: Tên thiết bị
            employee_count: Số lượng nhân viên đồng bộ
            status: Trạng thái (success/failed)
            message: Thông báo chi tiết
            
        Returns:
            True nếu ghi log thành công
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/resource/Sync History",
                json={
                    "doctype": "Sync History",
                    "sync_type": sync_type,
                    "device_name": device_name,
                    "employee_count": employee_count,
                    "status": status,
                    "sync_datetime": datetime.now().isoformat(),
                    "message": message
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Ghi log đồng bộ thành công")
                return True
            else:
                logger.error(f"❌ Lỗi ghi log đồng bộ: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi ghi log đồng bộ: {str(e)}")
            return False
