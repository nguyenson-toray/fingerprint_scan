# main.py
"""
Ứng dụng quản lý vân tay nhân viên - ERPNext HRMS
Entry point chính của ứng dụng
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import os
import sys
from datetime import datetime
import json
from typing import List, Dict, Optional
from PIL import Image, ImageTk

# Import các module của dự án
from config import UI_CONFIG, LOG_CONFIG, FINGER_MAPPING, APP_INFO
from utils.logger import setup_logger
from core.erpnext_api import ERPNextAPI
from core.fingerprint_scanner import FingerprintScanner
from core.attendance_device_sync import AttendanceDeviceSync
from core.data_manager import DataManager
from gui.employee_management import EmployeeTab
from gui.dialogs import AttendanceIDDialog

# Thiết lập logging
logger = setup_logger()


class FingerprintApp:
    """Ứng dụng chính quản lý vân tay"""
    
    def __init__(self):
        # Khởi tạo cửa sổ chính
        self.root = ctk.CTk()
        self.root.title(UI_CONFIG["app_title"])
        self.root.geometry(f"{UI_CONFIG['window_width']}x{UI_CONFIG['window_height']}")
        
        # Set appearance mode từ config
        ctk.set_appearance_mode(UI_CONFIG.get("appearance_mode", "light"))
        
        # Safe theme loading with fallback
        try:
            ctk.set_default_color_theme(UI_CONFIG["theme"])
        except Exception as e:
            logger.warning(f"Could not load theme '{UI_CONFIG['theme']}': {str(e)}")
            logger.info("Using default blue theme as fallback")
            ctk.set_default_color_theme("blue")
        
        # Khởi tạo các core components
        self.data_manager = DataManager()
        self.erpnext_api = ERPNextAPI()
        self.scanner = FingerprintScanner()
        self.device_sync = AttendanceDeviceSync(self.erpnext_api)
        
        # Khởi tạo dữ liệu
        self.employees = []
        self.current_fingerprints = {}
        self.attendance_devices = []
        self.device_status = {}  # Thêm device status tracking
        self.selected_employee = None
        self.selected_finger_index = None
        
        # Flags trạng thái
        self.scanner_connected = False
        self.erpnext_connected = False
        self.is_connecting = False
        
        # Tải dữ liệu ban đầu
        self.load_initial_data()
        
        # Tạo giao diện
        self.create_ui()
        
        logger.info("🚀 Ứng dụng đã khởi tạo thành công")
    
    def load_initial_data(self):
        """Tải dữ liệu ban đầu từ local"""
        try:
            # Tải dữ liệu vân tay local với xử lý lỗi JSON
            try:
                self.current_fingerprints = self.data_manager.load_local_fingerprints()
                logger.info(f"✅ Đã tải {len(self.current_fingerprints)} nhân viên từ dữ liệu local")
            except Exception as json_error:
                logger.warning(f"⚠️ Không thể tải dữ liệu vân tay local: {str(json_error)}")
                self.current_fingerprints = {}
                logger.info("📝 Khởi tạo dữ liệu vân tay trống")
            
            # Tải cấu hình máy chấm công từ config.py
            self.attendance_devices = self.data_manager.load_device_config()
            logger.info(f"✅ Đã tải {len(self.attendance_devices)} máy chấm công từ config")
            
            # Tải danh sách nhân viên từ local
            self.load_employees_from_local()
            
        except Exception as e:
            logger.error(f"❌ Lỗi tải dữ liệu ban đầu: {str(e)}")
    
    def load_employees_from_local(self):
        """Tải danh sách nhân viên từ file local"""
        try:
            if os.path.exists("data/employees.json"):
                with open("data/employees.json", 'r', encoding='utf-8') as f:
                    self.employees = json.load(f)
                logger.info(f"✅ Đã tải {len(self.employees)} nhân viên từ file local")
                # Cập nhật UI sau khi tải
                self.root.after(0, lambda: self.employee_tab.update_employee_list())
            else:
                logger.info("📝 Chưa có file danh sách nhân viên local")
                self.employees = []
        except Exception as e:
            logger.error(f"❌ Lỗi tải danh sách nhân viên local: {str(e)}")
            self.employees = []
    
    def create_ui(self):
        """Tạo giao diện người dùng"""
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Content area - single view
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Employee management section
        self.employee_tab = EmployeeTab(content_frame, self)
        
        # Cập nhật UI ban đầu
        self.update_ui_state()
    
    def load_devices_from_erpnext_and_check(self):
        """Tải máy chấm công từ ERPNext và kiểm tra kết nối"""
        if not self.erpnext_connected:
            logger.warning("⚠️ Chưa kết nối ERPNext, thử kết nối...")
            if not self.connect_erpnext():
                logger.error("❌ Không thể kết nối ERPNext")
                return False
        
        def load_and_check_thread():
            try:
                logger.info("🔄 Đang tải danh sách máy chấm công từ ERPNext...")
                
                # Thử tải từ ERPNext
                devices_from_erpnext = self.erpnext_api.get_attendance_machines()
                
                if devices_from_erpnext:
                    self.attendance_devices = devices_from_erpnext
                    self.data_manager.save_device_config(self.attendance_devices)
                    logger.info(f"✅ Đã tải {len(self.attendance_devices)} máy chấm công từ ERPNext")
                else:
                    # Fallback 1: Tải từ file JSON
                    logger.info("📁 Thử tải từ file JSON local...")
                    try:
                        json_devices = self.data_manager.load_device_config()
                        if json_devices:
                            self.attendance_devices = json_devices
                            logger.info(f"✅ Đã tải {len(self.attendance_devices)} máy chấm công từ file JSON")
                        else:
                            raise Exception("Không có dữ liệu trong file JSON")
                    except Exception as json_error:
                        # Fallback 2: Tải từ config.py
                        logger.info("⚙️ Sử dụng cấu hình từ config.py...")
                        from config import ATTENDANCE_DEVICES
                        self.attendance_devices = ATTENDANCE_DEVICES.copy()
                        logger.info(f"✅ Đã tải {len(self.attendance_devices)} máy chấm công từ config.py")
                
                # Kiểm tra kết nối đến các thiết bị
                logger.info("🔍 Đang kiểm tra kết nối đến các máy chấm công...")
                self.check_device_connections()
                
                # Cập nhật UI
                self.root.after(0, lambda: [
                    self.employee_tab.update_device_sync_section(),
                    self.update_ui_state()
                ])
                
                logger.info("✅ Hoàn thành tải và kiểm tra máy chấm công")
                return True
                
            except Exception as e:
                logger.error(f"❌ Lỗi tải và kiểm tra máy chấm công: {str(e)}")
                return False
        
        # Chạy trong thread riêng
        threading.Thread(target=load_and_check_thread, daemon=True).start()
        return True
    
    def check_device_connections(self):
        """Kiểm tra kết nối đến các máy chấm công"""
        import socket
        
        self.device_status = {}
        
        for device in self.attendance_devices:
            device_id = device.get('id')
            ip = device.get('ip', device.get('ip_address', ''))
            port = device.get('port', 4370)
            device_name = device.get('device_name', device.get('name', f'Device_{device_id}'))
            
            try:
                # Tạo socket với timeout ngắn
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)  # Giảm timeout xuống 1 giây
                
                # Thử kết nối
                result = sock.connect_ex((ip, port))
                sock.close()
                
                if result == 0:
                    self.device_status[device_id] = "connected"
                    logger.info(f"✅ {device_name} ({ip}) - Kết nối thành công")
                else:
                    self.device_status[device_id] = "disconnected"
                    logger.warning(f"❌ {device_name} ({ip}) - Mất kết nối")
            except Exception as e:
                self.device_status[device_id] = "error"
                logger.error(f"❌ {device_name} ({ip}) - Lỗi kết nối: {str(e)}")
            
            # Cập nhật UI sau mỗi thiết bị
            self.root.after(0, lambda: self.employee_tab.update_device_sync_section())
    
    def connect_scanner(self) -> bool:
        """Kết nối máy quét vân tay"""
        try:
            if self.scanner.connect():
                self.scanner_connected = True
                logger.info("✅ Đã kết nối máy quét vân tay")
                return True
            else:
                logger.error("❌ Không thể kết nối máy quét vân tay")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi kết nối scanner: {str(e)}")
            return False
    
    def connect_erpnext(self) -> bool:
        """Kết nối đến ERPNext"""
        if self.is_connecting:
            return False
        
        self.is_connecting = True
        try:
            if self.erpnext_api.test_connection():
                self.erpnext_connected = True
                logger.info("✅ Đã kết nối ERPNext")
                
                # Tải danh sách nhân viên sau khi kết nối thành công
                employees = self.erpnext_api.get_all_employees()
                if employees:
                    self.employees = employees
                    self.save_employees_to_local()
                    logger.info(f"✅ Lấy được {len(employees)} nhân viên từ ERPNext")
                    # Cập nhật UI
                    self.root.after(0, lambda: self.employee_tab.update_employee_list())
                return True
            else:
                logger.error("❌ Không thể kết nối ERPNext")
                return False
        except Exception as e:
            logger.error(f"❌ Lỗi kết nối ERPNext: {str(e)}")
            return False
        finally:
            self.is_connecting = False
    
    def save_employees_to_local(self):
        """Lưu danh sách nhân viên vào file local"""
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/employees.json", 'w', encoding='utf-8') as f:
                json.dump(self.employees, f, ensure_ascii=False, indent=4)
            logger.info(f"✅ Đã lưu {len(self.employees)} nhân viên vào file local")
        except Exception as e:
            logger.error(f"❌ Lỗi lưu danh sách nhân viên local: {str(e)}")
    
    def update_ui_state(self):
        """Cập nhật trạng thái giao diện"""
        try:
            # Cập nhật employee tab
            self.employee_tab.update_employee_list()
            self.employee_tab.update_connection_status(
                self.scanner_connected, 
                self.erpnext_connected
            )
            
        except Exception as e:
            logger.error(f"❌ Lỗi cập nhật UI: {str(e)}")
    
    def set_selected_finger(self, employee, finger_index):
        """Thiết lập ngón tay được chọn"""
        self.selected_employee = employee
        self.selected_finger_index = finger_index
    
    def scan_fingerprint(self):
        """Quét vân tay cho ngón được chọn"""
        if not self.scanner_connected:
            messagebox.showerror("Lỗi", "Máy quét vân tay chưa được kết nối!")
            return
        
        if not self.selected_employee or self.selected_finger_index is None:
            messagebox.showerror("Lỗi", "Vui lòng chọn nhân viên và ngón tay!")
            return
        
        def scan_thread():
            try:
                # Quét vân tay
                template_data = self.scanner.enroll_fingerprint(self.selected_finger_index)
                
                if template_data:
                    # Encode template data
                    import base64
                    template_b64 = base64.b64encode(template_data).decode('utf-8')
                    
                    # Lưu vào dữ liệu hiện tại
                    employee_id = self.selected_employee['employee']
                    
                    if employee_id not in self.current_fingerprints:
                        self.current_fingerprints[employee_id] = {
                            'name': self.selected_employee['name'],
                            'employee': employee_id,
                            'employee_name': self.selected_employee['employee_name'],
                            'attendance_device_id': self.selected_employee.get('attendance_device_id', ''),
                            'password': self.selected_employee.get('custom_attendance_password', '123456'),
                            'privilege': self.selected_employee.get('custom_attendance_privilege', 0),
                            'fingerprints': []
                        }
                    
                    # Xóa vân tay cũ cho ngón này (nếu có)
                    fingerprints = self.current_fingerprints[employee_id]['fingerprints']
                    fingerprints = [fp for fp in fingerprints if fp['finger_index'] != self.selected_finger_index]
                    
                    # Thêm vân tay mới
                    finger_name = FINGER_MAPPING.get(self.selected_finger_index, f"Ngón {self.selected_finger_index}")
                    fingerprints.append({
                        'finger_index': self.selected_finger_index,
                        'finger_name': finger_name,
                        'template_data': template_b64,
                        'quality_score': 70
                    })
                    
                    self.current_fingerprints[employee_id]['fingerprints'] = fingerprints
                    
                    # Cập nhật UI
                    self.root.after(0, lambda: [
                        messagebox.showinfo("Thành công", f"Đã quét thành công vân tay {finger_name}!"),
                        self.employee_tab.update_fingerprint_display() if hasattr(self.employee_tab, 'update_fingerprint_display') else None
                    ])
                    
                    logger.info(f"✅ Đã quét thành công vân tay {finger_name} cho {employee_id}")
                else:
                    self.root.after(0, lambda: messagebox.showerror("Lỗi", "Quét vân tay thất bại!"))
                    
            except Exception as e:
                logger.error(f"❌ Lỗi quét vân tay: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi quét vân tay: {str(e)}"))
        
        # Chạy trong thread riêng
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def save_fingerprints(self):
        """Lưu dữ liệu vân tay"""
        try:
            # Kiểm tra nhân viên chưa có attendance_device_id
            employees_without_id = []
            for emp_id, emp_data in self.current_fingerprints.items():
                if not emp_data.get('attendance_device_id') or str(emp_data.get('attendance_device_id')).strip() == '':
                    employees_without_id.append(emp_data)
            
            # Nếu có nhân viên chưa có ID, hiển thị dialog
            if employees_without_id:
                dialog = AttendanceIDDialog(self.root, employees_without_id)
                if dialog.result:
                    # Gán ID tự động và cập nhật ERPNext
                    self.assign_attendance_ids(employees_without_id)
            
            # Lưu vào file local
            self.data_manager.save_local_fingerprints(self.current_fingerprints)
            
            # Lưu vào ERPNext nếu có kết nối
            if self.erpnext_connected:
                self.save_to_erpnext()
            
            messagebox.showinfo("Thành công", "Đã lưu dữ liệu vân tay thành công!")
            logger.info("✅ Đã lưu dữ liệu vân tay")
            
        except Exception as e:
            logger.error(f"❌ Lỗi lưu dữ liệu: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi lưu dữ liệu: {str(e)}")
    
    def assign_attendance_ids(self, employees_without_id):
        """Gán attendance_device_id tự động"""
        try:
            # Tìm ID lớn nhất hiện tại
            max_id = 0
            
            # Kiểm tra trong current_fingerprints
            for emp_data in self.current_fingerprints.values():
                try:
                    current_id = int(emp_data.get('attendance_device_id', 0))
                    max_id = max(max_id, current_id)
                except ValueError:
                    pass
            
            # Kiểm tra trong employees từ ERPNext
            for emp in self.employees:
                try:
                    current_id = int(emp.get('attendance_device_id', 0))
                    max_id = max(max_id, current_id)
                except ValueError:
                    pass
            
            # Gán ID tăng dần
            for emp_data in employees_without_id:
                max_id += 1
                emp_data['attendance_device_id'] = str(max_id)
                
                # Cập nhật ERPNext
                if self.erpnext_connected:
                    self.erpnext_api.update_employee_attendance_device_id(
                        emp_data['name'], 
                        max_id
                    )
                
                logger.info(f"✅ Đã gán ID {max_id} cho {emp_data['employee']}")
            
        except Exception as e:
            logger.error(f"❌ Lỗi gán attendance_device_id: {str(e)}")
    
    def save_to_erpnext(self):
        """Lưu dữ liệu vân tay vào ERPNext"""
        try:
            for emp_id, emp_data in self.current_fingerprints.items():
                for fp in emp_data.get('fingerprints', []):
                    # Decode base64 template
                    import base64
                    template_bytes = base64.b64decode(fp['template_data'])
                    
                    # Lưu vào ERPNext
                    self.erpnext_api.save_fingerprint_to_employee(
                        emp_data['name'],
                        fp['finger_index'],
                        template_bytes,
                        fp.get('quality_score', 70)
                    )
            
            logger.info("✅ Đã lưu dữ liệu vân tay vào ERPNext")
            
        except Exception as e:
            logger.error(f"❌ Lỗi lưu vào ERPNext: {str(e)}")
    
    def sync_to_devices(self, selected_devices):
        """Đồng bộ dữ liệu đến máy chấm công"""
        if not self.current_fingerprints:
            messagebox.showwarning("Cảnh báo", "Không có dữ liệu vân tay để đồng bộ!")
            return
        
        def sync_thread():
            try:
                # Chuẩn bị dữ liệu đồng bộ
                employees_to_sync = []
                for emp_data in self.current_fingerprints.values():
                    if emp_data.get('fingerprints') and emp_data.get('attendance_device_id'):
                        employees_to_sync.append(emp_data)
                
                if not employees_to_sync:
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Cảnh báo", 
                        "Không có nhân viên nào có đủ dữ liệu để đồng bộ!"
                    ))
                    return
                
                # Đồng bộ đến các thiết bị được chọn
                results = {}
                for device in selected_devices:
                    # Đảm bảo device có đủ thông tin cần thiết
                    if not device.get('name'):
                        device['name'] = device.get('device_name', f"Device_{device.get('id', 1)}")
                    
                    device_name = device.get('device_name', device.get('name', 'Unknown'))
                    logger.info(f"🔄 Đồng bộ đến thiết bị: {device_name}")
                    success, total = self.device_sync.sync_to_device(device, employees_to_sync)
                    results[device_name] = (success, total)
                
                # Hiển thị kết quả
                result_text = "Kết quả đồng bộ:\n"
                for device_name, (success, total) in results.items():
                    result_text += f"• {device_name}: {success}/{total} nhân viên\n"
                
                self.root.after(0, lambda: messagebox.showinfo("Hoàn thành", result_text))
                
            except Exception as e:
                logger.error(f"❌ Lỗi đồng bộ: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi đồng bộ: {str(e)}"))
        
        # Chạy trong thread riêng
        threading.Thread(target=sync_thread, daemon=True).start()
    
    def run(self):
        """Chạy ứng dụng"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            logger.error(f"❌ Lỗi chạy ứng dụng: {str(e)}")
    
    def on_closing(self):
        """Xử lý khi đóng ứng dụng"""
        try:
            # Ngắt kết nối các thiết bị
            if self.scanner_connected:
                self.scanner.disconnect()
            
            self.device_sync.disconnect_all_devices()
            
            logger.info("👋 Đã đóng ứng dụng")
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi đóng ứng dụng: {str(e)}")
            self.root.destroy()


def main():
    """Hàm main khởi chạy ứng dụng"""
    try:
        app = FingerprintApp()
        app.run()
        
    except ImportError as e:
        print(f"❌ Lỗi import module: {str(e)}")
        print("Vui lòng kiểm tra cài đặt và các module cần thiết.")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Lỗi khởi chạy ứng dụng: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()