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
    
    def check_required_doctypes(self) -> Dict[str, bool]:
        """
        Kiểm tra các DocType cần thiết có tồn tại trong ERPNext hay không
        
        Returns:
            Dict với key là tên DocType, value là True/False tùy vào DocType có tồn tại
        """
        required_doctypes = [
            "Attendance Machine",
            "Sync History"
        ]
        
        doctypes_status = {}
        
        for doctype_name in required_doctypes:
            try:
                # Kiểm tra xem DocType có tồn tại không
                response = self.session.get(
                    f"{self.base_url}/api/resource/DocType/{doctype_name}"
                )
                
                if response.status_code == 200:
                    doctypes_status[doctype_name] = True
                    logger.info(f"✅ DocType '{doctype_name}' đã tồn tại")
                elif response.status_code == 404:
                    doctypes_status[doctype_name] = False
                    logger.warning(f"⚠️ DocType '{doctype_name}' chưa tồn tại")
                else:
                    doctypes_status[doctype_name] = False
                    logger.error(f"❌ Lỗi kiểm tra DocType '{doctype_name}': {response.status_code}")
                    
            except Exception as e:
                doctypes_status[doctype_name] = False
                logger.error(f"❌ Lỗi khi kiểm tra DocType '{doctype_name}': {str(e)}")
        
        return doctypes_status
    
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
                        "designation", "status"
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
    
    def get_employee_fingerprints(self, employee_id: str) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu vân tay của nhân viên
        
        Args:
            employee_id: Mã nhân viên
            
        Returns:
            Danh sách dữ liệu vân tay
        """
        # Chức năng này sẽ không được sử dụng để tải template từ ERPNext theo yêu cầu mới
        # Tuy nhiên, giữ lại để có thể tải thông tin về ngón tay đã đăng ký nếu cần
        try:
            # Lấy dữ liệu từ bảng Fingerprint Data
            response = self.session.get(
                f"{self.base_url}/api/resource/Fingerprint Data",
                params={
                    "fields": json.dumps([
                        "name", "employee", "finger_index", 
                        "quality_score", # Không lấy template_data nữa
                        "enrolled_date", "last_updated"
                    ]),
                    "filters": json.dumps([["employee", "=", employee_id]]),
                    "order_by": "finger_index"
                }
            )
            
            if response.status_code == 200:
                fingerprints = response.json().get("data", [])
                logger.info(f"✅ Lấy được {len(fingerprints)} vân tay của nhân viên {employee_id}")
                return fingerprints
            else:
                logger.error(f"❌ Lỗi khi lấy dữ liệu vân tay: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi lấy dữ liệu vân tay: {str(e)}")
            return []
    
    def save_fingerprint_to_employee(self, employee_name: str, finger_index: int, 
                                   template_data: bytes, quality_score: int = 0) -> bool:
        """
        Lưu dữ liệu vân tay vào ERPNext thông qua child table của Employee
        
        Args:
            employee_name: Tên của nhân viên (doc.name trong ERPNext)
            finger_index: Chỉ số ngón tay (0-9)
            template_data: Dữ liệu template vân tay
            quality_score: Điểm chất lượng vân tay
            
        Returns:
            True nếu lưu thành công, False nếu thất bại
        """
        try:
            # Encode template data to base64
            template_b64 = base64.b64encode(template_data).decode('utf-8')
            
            # Lấy thông tin nhân viên hiện tại
            emp_response = self.session.get(f"{self.base_url}/api/resource/Employee/{employee_name}")
            
            if emp_response.status_code != 200:
                logger.error(f"❌ Không thể lấy thông tin nhân viên: {employee_name}")
                return False
            
            employee_doc = emp_response.json().get("data", {})
            
            # Lấy danh sách vân tay hiện tại (nếu có child table)
            current_fingerprints = employee_doc.get("custom_fingerprint_data", [])
            
            # Tìm và cập nhật vân tay hiện có hoặc thêm mới
            found = False
            for fp in current_fingerprints:
                if fp.get("finger_index") == finger_index:
                    fp["template_data"] = template_b64
                    fp["quality_score"] = quality_score
                    fp["last_updated"] = datetime.now().isoformat()
                    found = True
                    break
            
            if not found:
                # Thêm vân tay mới
                current_fingerprints.append({
                    "finger_index": finger_index,
                    "template_data": template_b64,
                    "quality_score": quality_score,
                    "enrolled_date": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                })
            
            # Cập nhật Employee document
            update_response = self.session.put(
                f"{self.base_url}/api/resource/Employee/{employee_name}",
                json={
                    "custom_fingerprint_data": current_fingerprints
                }
            )
            
            if update_response.status_code == 200:
                logger.info(f"✅ Lưu vân tay thành công cho {employee_name} - Ngón {finger_index}")
                return True
            else:
                logger.error(f"❌ Lỗi cập nhật vân tay: {update_response.status_code} - {update_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu vân tay: {str(e)}")
            return False
    
    def save_fingerprint(self, employee_id: str, finger_index: int, 
                        template_data: bytes, quality_score: int = 0) -> bool:
        """
        Lưu dữ liệu vân tay vào ERPNext
        
        Args:
            employee_id: Mã nhân viên
            finger_index: Chỉ số ngón tay (0-9)
            template_data: Dữ liệu template vân tay
            quality_score: Điểm chất lượng vân tay
            
        Returns:
            True nếu lưu thành công, False nếu thất bại
        """
        try:
            # Encode template data to base64
            template_b64 = base64.b64encode(template_data).decode('utf-8')
            
            # Kiểm tra xem đã có dữ liệu vân tay này chưa
            existing = self.session.get(
                f"{self.base_url}/api/resource/Fingerprint Data",
                params={
                    "filters": json.dumps([
                        ["employee", "=", employee_id],
                        ["finger_index", "=", finger_index]
                    ])
                }
            )
            
            if existing.status_code == 200 and existing.json().get("data"):
                # Update existing record
                doc_name = existing.json()["data"][0]["name"]
                
                response = self.session.put(
                    f"{self.base_url}/api/resource/Fingerprint Data/{doc_name}",
                    json={
                        "template_data": template_b64,
                        "quality_score": quality_score,
                        "last_updated": datetime.now().isoformat()
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Cập nhật vân tay thành công cho {employee_id} - Ngón {finger_index}")
                    return True
                else:
                    logger.error(f"❌ Lỗi cập nhật vân tay: {response.status_code}")
                    return False
            else:
                # Create new record
                response = self.session.post(
                    f"{self.base_url}/api/resource/Fingerprint Data",
                    json={
                        "doctype": "Fingerprint Data",
                        "employee": employee_id,
                        "finger_index": finger_index,
                        "template_data": template_b64,
                        "quality_score": quality_score,
                        "enrolled_date": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat()
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Lưu vân tay mới thành công cho {employee_id} - Ngón {finger_index}")
                    return True
                else:
                    logger.error(f"❌ Lỗi lưu vân tay: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu vân tay: {str(e)}")
            return False
    
    def delete_fingerprint(self, employee_id: str, finger_index: int) -> bool:
        """
        Xóa dữ liệu vân tay
        
        Args:
            employee_id: Mã nhân viên
            finger_index: Chỉ số ngón tay (0-9)
            
        Returns:
            True nếu xóa thành công, False nếu thất bại
        """
        try:
            # Tìm record cần xóa
            existing = self.session.get(
                f"{self.base_url}/api/resource/Fingerprint Data",
                params={
                    "filters": json.dumps([
                        ["employee", "=", employee_id],
                        ["finger_index", "=", finger_index]
                    ])
                }
            )
            
            if existing.status_code == 200 and existing.json().get("data"):
                doc_name = existing.json()["data"][0]["name"]
                
                # Xóa record
                response = self.session.delete(
                    f"{self.base_url}/api/resource/Fingerprint Data/{doc_name}"
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Xóa vân tay thành công cho {employee_id} - Ngón {finger_index}")
                    return True
                else:
                    logger.error(f"❌ Lỗi xóa vân tay: {response.status_code}")
                    return False
            else:
                logger.warning(f"⚠️ Không tìm thấy vân tay để xóa")
                return True
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi xóa vân tay: {str(e)}")
            return False
    
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

    def get_attendance_device_mapping(self) -> Dict[str, str]:
        """
        Lấy mapping giữa employee và attendance_device_id
        
        Returns:
            Dict với key là employee, value là attendance_device_id
        """
        try:
            employees = self.get_all_employees()
            mapping = {}
            
            for emp in employees:
                if emp.get("attendance_device_id"):
                    mapping[emp["employee"]] = emp["attendance_device_id"]
                    
            logger.info(f"✅ Lấy được mapping cho {len(mapping)} nhân viên")
            return mapping
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi lấy mapping: {str(e)}")
            return {}
    
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
                logger.error(f"❌ Lỗi ghi log đồng bộ: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi ghi log đồng bộ: {str(e)}")
            return False