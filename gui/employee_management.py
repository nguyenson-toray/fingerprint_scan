"""
Tab quản lý nhân viên với thiết kế đơn tab và hiển thị trạng thái máy chấm công chi tiết
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, List, Optional
from config import FINGER_MAPPING
import threading
import json

logger = logging.getLogger(__name__)

class EmployeeTab:
    """Tab quản lý nhân viên với enhanced UI và device status display"""
    
    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.create_widgets()
    
    def create_widgets(self):
        """Tạo các widget cho tab nhân viên với layout cân đối"""
        # Main container
        main_frame = ctk.CTkFrame(self.parent)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left side: Employee list (width cân đối với right side)
        left_frame = ctk.CTkFrame(main_frame, width=400)
        left_frame.pack(side="left", fill="y", padx=(0, 5))
        left_frame.pack_propagate(False)
        
        self.create_employee_panel(left_frame)
        
        # Middle section: Finger selection and actions
        middle_frame = ctk.CTkFrame(main_frame, width=320)
        middle_frame.pack(side="left", fill="y", padx=5)
        middle_frame.pack_propagate(False)
        
        self.create_control_panel(middle_frame)
        
        # Right side: Connection controls and activity log (width cân đối với left)
        right_frame = ctk.CTkFrame(main_frame, width=400)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        right_frame.pack_propagate(False)
        
        self.create_log_panel(right_frame)
    
    def create_employee_panel(self, parent):
        """Tạo panel danh sách nhân viên"""
        # Employee list frame
        emp_frame = ctk.CTkFrame(parent)
        emp_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Title and refresh button
        title_frame = ctk.CTkFrame(emp_frame)
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ctk.CTkLabel(title_frame, text="👥 Danh sách nhân viên", 
                                 font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(side="left")
        
        # Add refresh employee list button with icon
        self.refresh_employee_btn = ctk.CTkButton(
            title_frame, 
            text="🔄 Làm mới", 
            command=self.refresh_employee_list_safe,
            width=100
        )
        self.refresh_employee_btn.pack(side="right", padx=(10, 0))
        
        # Search box
        search_frame = ctk.CTkFrame(emp_frame)
        search_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(search_frame, text="🔍 Tìm kiếm:").pack(side="left", padx=(10, 5), pady=10)
        
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.on_search_changed)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=220)
        search_entry.pack(side="left", padx=(0, 10), pady=10)
        
        # Employee list
        list_frame = ctk.CTkFrame(emp_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Treeview for employees
        columns = ("employee", "name", "custom_group", "device_id")
        self.employee_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)
        
        # Configure columns
        self.employee_tree.heading("employee", text="Mã NV")
        self.employee_tree.heading("name", text="Tên nhân viên")
        self.employee_tree.heading("custom_group", text="Nhóm")
        self.employee_tree.heading("device_id", text="ID CC")
        
        self.employee_tree.column("employee", width=80)
        self.employee_tree.column("name", width=160)
        self.employee_tree.column("custom_group", width=90)
        self.employee_tree.column("device_id", width=60)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.employee_tree.yview)
        self.employee_tree.configure(yscrollcommand=scrollbar.set)
        
        self.employee_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind selection event
        self.employee_tree.bind("<<TreeviewSelect>>", self.on_employee_select)
    
    def create_control_panel(self, parent):
        """Tạo panel điều khiển với color-coded finger buttons"""
        # Finger selection section
        finger_frame = ctk.CTkFrame(parent)
        finger_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(finger_frame, text="👆 Chọn ngón tay", 
                   font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Finger buttons arranged in left/right hands
        hands_frame = ctk.CTkFrame(finger_frame)
        hands_frame.pack(padx=10, pady=(0, 10))
        
        # Left hand column
        left_hand_frame = ctk.CTkFrame(hands_frame)
        left_hand_frame.pack(side="left", padx=(10, 5), pady=10)
        
        ctk.CTkLabel(left_hand_frame, text="👈 Tay trái", 
                   font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 10))
        
        # Right hand column
        right_hand_frame = ctk.CTkFrame(hands_frame)
        right_hand_frame.pack(side="right", padx=(5, 10), pady=10)
        
        ctk.CTkLabel(right_hand_frame, text="👉 Tay phải", 
                   font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 10))
        
        self.finger_buttons = {}
        
        # Left hand fingers (0-4)
        for i in range(5):
            finger_name = FINGER_MAPPING[i].replace(" trái", "")
            btn = ctk.CTkButton(
                left_hand_frame, 
                text=f"{i}: {finger_name}", 
                width=130,
                command=lambda idx=i: self.select_finger(idx)
            )
            btn.pack(pady=2, padx=5)
            # Thêm binding cho double click
            btn.bind('<Double-Button-1>', lambda e, idx=i: self.on_finger_button_double_click(idx))
            self.finger_buttons[i] = btn
        
        # Right hand fingers (5-9)
        for i in range(5, 10):
            finger_name = FINGER_MAPPING[i].replace(" phải", "")
            btn = ctk.CTkButton(
                right_hand_frame, 
                text=f"{i}: {finger_name}", 
                width=130,
                command=lambda idx=i: self.select_finger(idx)
            )
            btn.pack(pady=2, padx=5)
            # Thêm binding cho double click
            btn.bind('<Double-Button-1>', lambda e, idx=i: self.on_finger_button_double_click(idx))
            self.finger_buttons[i] = btn
        
        # Action buttons with icons - horizontal layout
        action_frame = ctk.CTkFrame(parent)
        action_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(action_frame, text="⚡ Thao tác", 
                   font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Button container for horizontal layout
        button_container = ctk.CTkFrame(action_frame)
        button_container.pack(pady=5, padx=10)
        
        self.scan_btn = ctk.CTkButton(button_container, text="👆 Thêm vân tay", 
                                    command=self.main_app.scan_fingerprint,
                                    width=130)
        self.scan_btn.pack(side="left", padx=(10, 5), pady=5)
        
        self.save_btn = ctk.CTkButton(button_container, text="💾 Lưu", 
                                    command=self.main_app.save_fingerprints,
                                    width=130)
        self.save_btn.pack(side="left", padx=(5, 10), pady=5)
        
        # Add new button for saving to ERPNext
        self.save_to_erpnext_btn = ctk.CTkButton(
            action_frame,
            text="🌐 Lưu lên ERPNext",
            command=self.main_app.save_to_erpnext,
            height=40
        )
        self.save_to_erpnext_btn.pack(side="left", padx=10, pady=5, fill="x", expand=True)
        
        # Enhanced sync section với device status display
        self.create_device_sync_section(parent)
    
    def create_device_sync_section(self, parent):
        """Tạo section đồng bộ máy chấm công với device status"""
        sync_frame = ctk.CTkFrame(parent)
        sync_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(sync_frame, text="🔄 Đồng bộ máy chấm công", 
                   font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Removed device_connection_btn from here
        
        # Sync button
        self.sync_btn = ctk.CTkButton(sync_frame, text="📤 Đồng bộ", 
                                    command=self.sync_to_selected_devices,
                                    width=250)
        self.sync_btn.pack(pady=(5, 10))
        
        # Device selection với enhanced status display
        device_selection_frame = ctk.CTkScrollableFrame(sync_frame, height=120)
        device_selection_frame.pack(fill="x", padx=10, pady=5)
        
        # Select all checkbox
        self.select_all_var = ctk.BooleanVar()
        select_all_cb = ctk.CTkCheckBox(
            device_selection_frame, 
            text="✅ Chọn tất cả thiết bị",
            variable=self.select_all_var,
            command=self.toggle_all_devices
        )
        select_all_cb.pack(anchor="w", pady=2)
        
        # Container cho device checkboxes
        self.device_checkboxes_frame = ctk.CTkFrame(device_selection_frame)
        self.device_checkboxes_frame.pack(fill="x", pady=5)
        
        # Initialize device checkboxes
        self.device_vars = {}
        self.device_checkboxes = {}
        self.update_device_sync_section() 
    
    def update_device_sync_section(self):
        """Cập nhật section đồng bộ với device status chi tiết"""
        # Clear existing checkboxes
        for widget in self.device_checkboxes_frame.winfo_children():
            widget.destroy()
        
        self.device_vars = {}
        self.device_checkboxes = {}
        
        # Create checkboxes for each device với status display
        for device in self.main_app.attendance_devices:
            device_id = device.get('id')
            device_name = device.get('device_name', device.get('name', f'Device_{device_id}'))
            ip_address = device.get('ip', device.get('ip_address', 'Unknown'))
            
            # Get device status
            status = self.main_app.device_status.get(device_id, 'unknown')
            if status == 'connected':
                status_icon = "🟢"
                status_text = "Kết nối"
            elif status == 'disconnected':
                status_icon = "🔴"
                status_text = "Ngắt kết nối"
            elif status == 'error':
                status_icon = "🟡"
                status_text = "Lỗi"
            else:
                status_icon = "⚪"
                status_text = "Chưa kiểm tra"
            
            # Device info frame
            device_frame = ctk.CTkFrame(self.device_checkboxes_frame)
            device_frame.pack(fill="x", pady=2, padx=5)
            
            # Checkbox - checked by default
            var = ctk.BooleanVar(value=True)
            checkbox = ctk.CTkCheckBox(
                device_frame,
                text="",
                variable=var,
                width=20
            )
            checkbox.pack(side="left", padx=(5, 10), pady=5)
            
            # Device info label với format: {Tên máy} - {ip_address} - {icon status}
            info_text = f"{device_name} - {ip_address} - {status_icon} {status_text}"
            info_label = ctk.CTkLabel(
                device_frame,
                text=info_text,
                font=ctk.CTkFont(size=11),
                anchor="w"
            )
            info_label.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=5)
            
            self.device_vars[device_id] = var
            self.device_checkboxes[device_id] = checkbox
        
        # Set select all checkbox to checked by default
        self.select_all_var.set(True)
    
    def create_log_panel(self, parent):
        """Tạo panel kết nối và nhật ký với width cân đối"""
        # Connection controls at top
        connection_frame = ctk.CTkFrame(parent)
        connection_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        ctk.CTkLabel(connection_frame, text="🔌 Kết nối thiết bị:", 
                   font=ctk.CTkFont(size=14, weight="bold")).pack(side="top", pady=(10, 5))
        
        # Connection buttons row
        button_row1 = ctk.CTkFrame(connection_frame)
        button_row1.pack(fill="x", padx=5, pady=5)
        
        # Scanner connection button
        self.scanner_btn = ctk.CTkButton(
            button_row1, 
            text="📷 Scanner", 
            command=self.manual_connect_scanner,
            width=120,
            fg_color="red"
        )
        self.scanner_btn.pack(side="left", padx=5)
        
        # ERPNext connection button
        self.erpnext_btn = ctk.CTkButton(
            button_row1, 
            text="🌐 ERPNext", 
            command=self.manual_connect_erpnext,
            width=120,
            fg_color="red"
        )
        self.erpnext_btn.pack(side="left", padx=5)
        
        # Device connection button - moved here after erpnext_btn
        self.device_connection_btn = ctk.CTkButton(
            button_row1,
            text="🖥️ Máy chấm công",
            command=self.connect_attendance_devices,
            width=120,
            fg_color="red"
        )
        self.device_connection_btn.pack(side="left", padx=5)
         # Add "Tải vân tay chừ MCC" button after device_connection_btn
        self.load_from_device_btn = ctk.CTkButton(
            button_row1,
            text="📥 Tải vân tay từ MCC",
            command=self.load_fingerprints_from_device,
            width=140,
            fg_color="blue"
        )
        self.load_from_device_btn.pack(side="right", padx=5)
        # Activity log section
        self.log_frame = ctk.CTkFrame(parent)
        self.log_frame.pack(fill="both", expand=True, padx=5, pady=(5, 5))
        
        ctk.CTkLabel(self.log_frame, text="📝 Nhật ký hoạt động", 
                   font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Create log text widget with scrollbar
        self.log_text = tk.Text(self.log_frame, height=15, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Setup log display với color highlighting
        self.setup_log_display()
    
    def setup_log_display(self):
        """Thiết lập hiển thị log với màu sắc"""
        class ColoredGUILogHandler(logging.Handler):
            def __init__(self, text_widget, main_app):
                super().__init__()
                self.text_widget = text_widget
                self.main_app = main_app
                
                # Định nghĩa màu sắc cho các level
                self.colors = {
                    'DEBUG': '#808080',    # Gray
                    'INFO': '#0000FF',     # Blue
                    'WARNING': '#FFA500',  # Orange
                    'ERROR': '#FF0000',    # Red
                    'CRITICAL': '#800000'  # Dark Red
                }
                
                # Định nghĩa icon cho các level
                self.icons = {
                    'DEBUG': '🔍',
                    'INFO': 'ℹ️',
                    'WARNING': '⚠️',
                    'ERROR': '❌',
                    'CRITICAL': '💥'
                }
            
            def emit(self, record):
                msg = self.format(record)
                self.append_colored_log(msg, record.levelname)
            
            def append_colored_log(self, message, level):
                # Thêm icon và màu sắc dựa trên level
                icon = self.icons.get(level, '')
                color = self.colors.get(level, '#000000')
                
                # Tạo tag cho đoạn text này
                tag = f"log_{level.lower()}"
                
                # Cấu hình tag với màu sắc
                self.text_widget.tag_configure(tag, foreground=color)
                
                # Thêm text với tag
                self.text_widget.insert('end', f"{icon} {message}\n", tag)
                
                # Tự động cuộn xuống
                self.text_widget.see('end')
                
                # Giới hạn số dòng log
                max_lines = 1000
                if int(self.text_widget.index('end-1c').split('.')[0]) > max_lines:
                    self.text_widget.delete('1.0', '2.0')
        
        # Thêm handler
        handler = ColoredGUILogHandler(self.log_text, self.main_app)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logger.addHandler(handler)
    def load_fingerprints_from_device(self):
        """Tải vân tay từ máy chấm công với tối ưu tốc độ - Strategy hybrid"""
        import os
        import base64
        import json
        import threading
        import concurrent.futures
        from tkinter import messagebox
        from config import FINGER_MAPPING
        
        if not self.main_app.attendance_devices:
            messagebox.showwarning("Cảnh báo", "Chưa tải danh sách máy chấm công!")
            return
        
        # Hiển thị dialog xác nhận
        if not messagebox.askyesno("Xác nhận", 
                                "Tải vân tay từ máy chấm công sẽ mất một chút thời gian.\n"
                                "Bạn có muốn tiếp tục không?"):
            return
        
        self.load_from_device_btn.configure(text="⏳ Đang tải...", state="disabled")
        
        def load_thread():
            try:
                # 1. Load danh sách employees từ employees.json để lọc
                employees_to_load, attendance_device_mapping = self._prepare_employee_mapping()
                
                if not employees_to_load:
                    self.main_app.root.after(0, lambda: [
                        self.load_from_device_btn.configure(text="📥 Tải vân tay từ MCC", state="normal"),
                        messagebox.showinfo("Thông báo", "Không có nhân viên nào có attendance_device_id hợp lệ để load!")
                    ])
                    return
                
                # 2. Load dữ liệu từ từng thiết bị với strategy tối ưu
                device_sync = self.main_app.device_sync
                fingerprints_from_device = {}
                total_loaded = 0
                
                for device in self.main_app.attendance_devices:
                    device_name = device.get('device_name', device.get('name', f"Device_{device.get('id', 1)}"))
                    logger.info(f"🔄 Đang kết nối với {device_name}...")
                    
                    # Kết nối thiết bị
                    zk = device_sync.connect_device(device)
                    if not zk:
                        logger.error(f"❌ Không thể kết nối đến {device_name}")
                        continue
                    
                    try:
                        # Lấy users và map với attendance_device_id
                        device_users = zk.get_users()
                        target_users = [user for user in device_users if user.user_id in attendance_device_mapping]
                        
                        logger.info(f"🎯 Sẽ load vân tay cho {len(target_users)} users từ {device_name}")
                        
                        # Load fingerprints với strategy tối ưu
                        device_fingerprints = self._load_fingerprints_optimized(
                            zk, target_users, attendance_device_mapping, device_name
                        )
                        
                        # Merge dữ liệu
                        fingerprints_from_device.update(device_fingerprints)
                        total_loaded += len([fp for fp in device_fingerprints.values() if fp.get('fingerprints')])
                        
                    except Exception as device_err:
                        logger.error(f"❌ Lỗi khi load dữ liệu từ {device_name}: {str(device_err)}")
                    finally:
                        # Ngắt kết nối
                        device_id = device.get('id', 1)
                        device_sync.disconnect_device(device_id)
                
                # 3. Lưu và merge dữ liệu
                self._save_and_merge_fingerprints(fingerprints_from_device, len(employees_to_load), total_loaded)
                
            except Exception as e:
                logger.error(f"❌ Lỗi tải vân tay từ máy chấm công: {str(e)}")
                self.main_app.root.after(0, lambda: [
                    self.load_from_device_btn.configure(text="📥 Tải vân tay từ MCC", state="normal"),
                    messagebox.showerror("Lỗi", f"Lỗi tải vân tay từ máy chấm công: {str(e)}")
                ])
        
        # Run in thread
        threading.Thread(target=load_thread, daemon=True).start()

    def _prepare_employee_mapping(self):
        """Chuẩn bị mapping employees và attendance_device_id"""
        import os
        import json
        
        employees_to_load = []
        attendance_device_mapping = {}
        
        try:
            if os.path.exists("data/employees.json"):
                with open("data/employees.json", 'r', encoding='utf-8') as f:
                    all_employees = json.load(f)
                
                # Lọc nhân viên có attendance_device_id hợp lệ
                for emp in all_employees:
                    attendance_id = emp.get('attendance_device_id')
                    if attendance_id and str(attendance_id).strip() and attendance_id != "0":
                        try:
                            attendance_id_int = int(attendance_id)
                            if attendance_id_int > 0:
                                employees_to_load.append(emp)
                                attendance_device_mapping[attendance_id] = emp
                        except ValueError:
                            continue
                
                logger.info(f"📋 Sẽ load vân tay cho {len(employees_to_load)} nhân viên có attendance_device_id hợp lệ")
            else:
                logger.warning("⚠️ Không tìm thấy file employees.json")
                
        except Exception as e:
            logger.error(f"❌ Lỗi đọc file employees.json: {str(e)}")
            raise e
        
        return employees_to_load, attendance_device_mapping

    def _load_fingerprints_optimized(self, zk, target_users, attendance_device_mapping, device_name):
        """Load fingerprints với strategy tối ưu - Hybrid approach"""
        import base64
        from config import FINGER_MAPPING
        
        fingerprints_result = {}
        
        try:
            # === STRATEGY 1: Bulk load toàn bộ templates ===
            logger.info(f"🚀 [{device_name}] Thử load toàn bộ templates (Strategy 1)...")
            
            # Load toàn bộ templates một lần
            all_templates = zk.get_templates()
            logger.info(f"✅ [{device_name}] Đã load {len(all_templates)} templates")
            
            # Group templates theo user_id
            templates_by_user = {}
            for template in all_templates:
                uid = template.uid
                if uid not in templates_by_user:
                    templates_by_user[uid] = []
                templates_by_user[uid].append(template)
            
            logger.info(f"📊 [{device_name}] Grouped templates cho {len(templates_by_user)} users")
            
            # Process chỉ target users
            processed_count = 0
            for user in target_users:
                uid = int(user.uid)
                user_id = user.user_id
                employee_info = attendance_device_mapping[user_id]
                
                if uid in templates_by_user:
                    fingerprint_count = self._process_user_templates(
                        templates_by_user[uid], employee_info, fingerprints_result
                    )
                    
                    if fingerprint_count > 0:
                        processed_count += 1
                        logger.info(f"   ✅ [{processed_count}/{len(target_users)}] {employee_info['employee']} - {fingerprint_count} vân tay")
                    else:
                        logger.warning(f"   ⚠️ [{processed_count + 1}/{len(target_users)}] {employee_info['employee']} - Không có vân tay")
                else:
                    logger.warning(f"   ❌ User {user_id} (UID: {uid}) không có templates")
            
            logger.info(f"✅ [{device_name}] Strategy 1 thành công - Processed {processed_count} users")
            return fingerprints_result
            
        except Exception as bulk_error:
            logger.warning(f"⚠️ [{device_name}] Strategy 1 failed: {str(bulk_error)}")
            
            # === STRATEGY 2: Fallback to individual loading ===
            logger.info(f"🔄 [{device_name}] Fallback to Strategy 2 (individual loading)...")
            
            try:
                return self._load_fingerprints_individual(zk, target_users, attendance_device_mapping, device_name)
            except Exception as fallback_error:
                logger.error(f"❌ [{device_name}] Strategy 2 cũng failed: {str(fallback_error)}")
                return {}

    def _process_user_templates(self, templates, employee_info, fingerprints_result):
        """Process templates của 1 user"""
        import base64
        from config import FINGER_MAPPING
        
        employee_id = employee_info['employee']
        
        # Khởi tạo cấu trúc dữ liệu cho nhân viên
        if employee_id not in fingerprints_result:
            fingerprints_result[employee_id] = {
                'name': employee_info.get('name', ''),
                'employee': employee_id,
                'employee_name': employee_info['employee_name'],
                'attendance_device_id': employee_info.get('attendance_device_id', ''),
                'password': '',  # Sẽ được set từ user data
                'privilege': 0,  # Sẽ được set từ user data
                'fingerprints': []
            }
        
        fingerprint_count = 0
        
        # Process từng template
        for template in templates:
            try:
                if hasattr(template, 'template') and template.template:
                    finger_idx = template.fid  # finger ID
                    
                    # Validate finger index
                    if 0 <= finger_idx <= 9:
                        # Convert template to base64
                        template_b64 = base64.b64encode(template.template).decode('utf-8')
                        
                        # Get finger name
                        finger_name = FINGER_MAPPING.get(finger_idx, f"Ngón {finger_idx}")
                        
                        # Add to fingerprints
                        fingerprints_result[employee_id]['fingerprints'].append({
                            'finger_index': finger_idx,
                            'finger_name': finger_name,
                            'template_data': template_b64,
                            'quality_score': 70
                        })
                        
                        fingerprint_count += 1
                    
            except Exception as template_error:
                logger.warning(f"   ⚠️ Lỗi xử lý template finger {template.fid}: {str(template_error)}")
                continue
        
        return fingerprint_count

    def _load_fingerprints_individual(self, zk, target_users, attendance_device_mapping, device_name):
        """Fallback strategy: Load individual với threading có giới hạn"""
        import concurrent.futures
        import base64
        from config import FINGER_MAPPING
        
        fingerprints_result = {}
        
        def safe_get_template(uid, finger_idx):
            """Wrapper an toàn cho get_user_template"""
            try:
                return zk.get_user_template(uid, finger_idx)
            except Exception as e:
                logger.debug(f"   Template UID {uid} finger {finger_idx} failed: {str(e)}")
                return None
        
        # Process từng user với limited threading
        for i, user in enumerate(target_users, 1):
            uid = int(user.uid)
            user_id = user.user_id
            employee_info = attendance_device_mapping[user_id]
            
            logger.info(f"   👤 [{i}/{len(target_users)}] Loading {employee_info['employee']} (UID: {uid})")
            
            # Khởi tạo data structure
            employee_id = employee_info['employee']
            if employee_id not in fingerprints_result:
                fingerprints_result[employee_id] = {
                    'name': employee_info.get('name', ''),
                    'employee': employee_id,
                    'employee_name': employee_info['employee_name'],
                    'attendance_device_id': str(user_id),
                    'password': user.password or '',
                    'privilege': user.privilege or 0,
                    'fingerprints': []
                }
            
            # Load 10 fingers với threading
            fingerprint_count = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_finger = {
                    executor.submit(safe_get_template, uid, finger_idx): finger_idx 
                    for finger_idx in range(10)
                }
                
                for future in concurrent.futures.as_completed(future_to_finger, timeout=30):
                    finger_idx = future_to_finger[future]
                    try:
                        template = future.result(timeout=5)
                        
                        if template and hasattr(template, 'template') and template.template:
                            # Convert template to base64
                            template_b64 = base64.b64encode(template.template).decode('utf-8')
                            finger_name = FINGER_MAPPING.get(finger_idx, f"Ngón {finger_idx}")
                            
                            fingerprints_result[employee_id]['fingerprints'].append({
                                'finger_index': finger_idx,
                                'finger_name': finger_name,
                                'template_data': template_b64,
                                'quality_score': 70
                            })
                            
                            fingerprint_count += 1
                            
                    except Exception as finger_error:
                        logger.debug(f"   Finger {finger_idx} processing failed: {str(finger_error)}")
                        continue
            
            if fingerprint_count > 0:
                logger.info(f"   ✅ Loaded {fingerprint_count} fingerprints for {employee_id}")
            else:
                logger.warning(f"   ⚠️ No fingerprints found for {employee_id}")
        
        return fingerprints_result

    def _save_and_merge_fingerprints(self, fingerprints_from_device, total_employees, total_loaded):
        """Lưu và merge dữ liệu fingerprints"""
        import os
        import json
        
        try:
            os.makedirs("data", exist_ok=True)
            
            # Convert dict to list để lưu file
            fingerprints_list = list(fingerprints_from_device.values())
            
            with open("data/all_fingerprints_from_machine.json", 'w', encoding='utf-8') as f:
                json.dump(fingerprints_list, f, ensure_ascii=False, indent=4)
            
            logger.info(f"✅ Đã lưu {len(fingerprints_list)} nhân viên vào all_fingerprints_from_machine.json")
            
            # Merge dữ liệu với employees.json vào all_fingerprints.json
            merged_count = self.merge_fingerprints_data(fingerprints_from_device)
            
            # Load lại dữ liệu vân tay trong ứng dụng
            self.main_app.current_fingerprints = self.main_app.data_manager.load_local_fingerprints()
            
            # Update UI
            success_msg = (
                f"🚀 Load dữ liệu vân tay thành công!\n\n"
                f"📊 Kết quả chi tiết:\n"
                f"• Nhân viên cần load: {total_employees}\n"
                f"• Nhân viên có vân tay: {total_loaded}\n"
                f"• Tổng sau khi merge: {merged_count}\n\n"
                f"✅ Đã sử dụng strategy tối ưu bulk-load!"
            )
            
            self.main_app.root.after(0, lambda: [
                self.load_from_device_btn.configure(text="📥 Tải vân tay từ MCC", state="normal"),
                self.update_finger_button_colors(),
                self.update_employee_list(),
                messagebox.showinfo("Thành công", success_msg)
            ])
            
        except Exception as save_err:
            logger.error(f"❌ Lỗi lưu/merge dữ liệu: {str(save_err)}")
            self.main_app.root.after(0, lambda: [
                self.load_from_device_btn.configure(text="📥 Tải vân tay từ MCC", state="normal"),
                messagebox.showerror("Lỗi", f"Lỗi lưu/merge dữ liệu: {str(save_err)}")
            ])


    def manual_connect_scanner(self):
        """Kết nối scanner thủ công"""
        if self.main_app.scanner_connected:
            messagebox.showinfo("Thông báo", "Scanner đã được kết nối!")
            return
        
        self.scanner_btn.configure(text="Đang kết nối...", state="disabled")
        
        def connect_thread():
            try:
                success = self.main_app.connect_scanner()
                
                self.main_app.root.after(0, lambda: [
                    self.scanner_btn.configure(text="📷 Scanner", state="normal"),
                    self.update_connection_status(success, self.main_app.erpnext_connected),
                    messagebox.showinfo("Thành công" if success else "Lỗi", 
                                      "Đã kết nối Scanner thành công!" if success else "Không thể kết nối Scanner!")
                ])
                    
            except Exception as e:
                logger.error(f"❌ Lỗi kết nối scanner: {str(e)}")
                self.main_app.root.after(0, lambda: [
                    self.scanner_btn.configure(text="📷 Scanner", state="normal"),
                    messagebox.showerror("Lỗi", f"Lỗi kết nối Scanner: {str(e)}")
                ])
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def manual_connect_erpnext(self):
        """Kết nối ERPNext thủ công"""
        if self.main_app.erpnext_connected:
            messagebox.showinfo("Thông báo", "ERPNext đã được kết nối!")
            return
        
        self.erpnext_btn.configure(text="Đang kết nối...", state="disabled")
        
        def connect_thread():
            try:
                success = self.main_app.connect_erpnext()
                
                self.main_app.root.after(0, lambda: [
                    self.erpnext_btn.configure(text="🌐 ERPNext", state="normal"),
                    self.update_connection_status(self.main_app.scanner_connected, success),
                    self.update_employee_list() if success else None,
                    messagebox.showinfo("Thành công" if success else "Lỗi", 
                                      "Đã kết nối ERPNext thành công!" if success else "Không thể kết nối ERPNext!")
                ])
                    
            except Exception as e:
                logger.error(f"❌ Lỗi kết nối ERPNext: {str(e)}")
                self.main_app.root.after(0, lambda: [
                    self.erpnext_btn.configure(text="🌐 ERPNext", state="normal"),
                    messagebox.showerror("Lỗi", f"Lỗi kết nối ERPNext: {str(e)}")
                ])
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def connect_attendance_devices(self):
        """Kết nối máy chấm công với non-blocking approach"""
        self.device_connection_btn.configure(text="🔄 Đang kết nối...", state="disabled")
        
        def connect_devices_thread():
            try:
                # Gọi hàm load devices từ main app
                self.main_app.load_devices_from_erpnext_and_check()
                
                # Update UI sau khi load xong
                self.main_app.root.after(0, lambda: [
                    self.device_connection_btn.configure(text="🖥️ Kết nối máy chấm công", state="normal"),
                    messagebox.showinfo("Hoàn thành", "Đã tải danh sách máy chấm công!")
                ])
                    
            except Exception as e:
                logger.error(f"❌ Lỗi kết nối máy chấm công: {str(e)}")
                self.main_app.root.after(0, lambda: [
                    self.device_connection_btn.configure(text="🖥️ Kết nối máy chấm công", state="normal"),
                    messagebox.showerror("Lỗi", f"Lỗi kết nối máy chấm công: {str(e)}")
                ])
        
        threading.Thread(target=connect_devices_thread, daemon=True).start()
    
    def toggle_all_devices(self):
        """Toggle tất cả device checkboxes"""
        select_all = self.select_all_var.get()
        for var in self.device_vars.values():
            var.set(select_all)
    
    def sync_to_selected_devices(self):
        """Đồng bộ đến các thiết bị được chọn"""
        # Lấy danh sách devices được chọn
        selected_devices = []
        for device_id, var in self.device_vars.items():
            if var.get():
                # Find device by id
                for device in self.main_app.attendance_devices:
                    if device.get('id') == device_id:
                        selected_devices.append(device)
                        break
        
        if not selected_devices:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một thiết bị để đồng bộ!")
            return
        
        # Hiển thị thông tin confirm
        device_names = [d.get('device_name', d.get('name', 'Unknown')) for d in selected_devices]
        confirm_msg = f"Bạn có muốn đồng bộ dữ liệu vân tay đến {len(selected_devices)} thiết bị:\n"
        confirm_msg += "\n".join([f"• {name}" for name in device_names])
        
        if messagebox.askyesno("Xác nhận đồng bộ", confirm_msg):
            logger.info(f"🔄 Bắt đầu đồng bộ đến {len(selected_devices)} thiết bị")
            self.main_app.sync_to_devices(selected_devices)
    
    def refresh_employee_list_safe(self):
        """Làm mới danh sách nhân viên với thread safety"""
        if not self.main_app.erpnext_connected:
            messagebox.showwarning("Cảnh báo", "Chưa kết nối ERPNext!")
            return
        
        # Disable button to prevent multiple clicks
        self.refresh_employee_btn.configure(text="⏳ Đang tải...", state="disabled")
        
        def refresh_thread():
            try:
                # Reload employees from ERPNext
                new_employees = self.main_app.erpnext_api.get_all_employees()
                  # Update in main thread
                def update_ui():
                    try:
                        self.main_app.employees = new_employees
                        
                        # Lưu nhân viên vào file local
                        self.main_app.save_employees_to_local()
                        
                   
                        self.update_employee_list()
                        self.refresh_employee_btn.configure(text="🔄 Làm mới", state="normal")
                        messagebox.showinfo("Thành công", f"Đã cập nhật {len(new_employees)} nhân viên và vân tay từ ERPNext!")
                        logger.info(f"✅ Đã làm mới danh sách {len(new_employees)} nhân viên và dữ liệu vân tay")
                    except Exception as ui_error:
                        logger.error(f"❌ Lỗi cập nhật UI: {str(ui_error)}")
                        self.refresh_employee_btn.configure(text="🔄 Làm mới", state="normal")
                
                # Schedule UI update safely
                if self.main_app.root and self.main_app.root.winfo_exists():
                    self.main_app.root.after(0, update_ui)
                
            except Exception as e:
                logger.error(f"❌ Lỗi làm mới danh sách nhân viên: {str(e)}")
                
                def handle_error():
                    try:
                        self.refresh_employee_btn.configure(text="🔄 Làm mới", state="normal")
                        messagebox.showerror("Lỗi", f"Lỗi làm mới danh sách: {str(e)}")
                    except:
                        pass
                
                if self.main_app.root and self.main_app.root.winfo_exists():
                    self.main_app.root.after(0, handle_error)
        
        # Use daemon thread to prevent hanging
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def on_search_changed(self, *args):
        """Xử lý thay đổi tìm kiếm"""
        search_term = self.search_var.get().lower()
        self.filter_employees(search_term)
    
    def filter_employees(self, search_term: str):
        """Lọc danh sách nhân viên"""
        for item in self.employee_tree.get_children():
            self.employee_tree.delete(item)
        
        for emp in self.main_app.employees:
            if (search_term in emp.get('employee', '').lower() or 
                search_term in emp.get('employee_name', '').lower()):
                
                self.employee_tree.insert("", "end", values=(
                    emp.get('employee', ''),
                    emp.get('employee_name', ''),
                    emp.get('custom_group', ''),
                    emp.get('attendance_device_id', '')
                ))
    
    def on_employee_select(self, event):
        """Xử lý chọn nhân viên và cập nhật màu finger buttons"""
        selection = self.employee_tree.selection()
        if selection:
            item = self.employee_tree.item(selection[0])
            employee_id = item['values'][0]
            
            selected_emp = None
            for emp in self.main_app.employees:
                if emp.get('employee') == employee_id:
                    selected_emp = emp
                    break
            
            if selected_emp:
                self.main_app.selected_employee = selected_emp
                self.update_finger_button_colors()
                logger.info(f"📋 Đã chọn nhân viên: {selected_emp.get('employee_name', '')} ({employee_id})")
    
    def select_finger(self, finger_index: int):
        """Chọn ngón tay và cập nhật màu buttons"""
        if not self.main_app.selected_employee:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn nhân viên trước!")
            return
        
        self.main_app.set_selected_finger(self.main_app.selected_employee, finger_index)
        self.update_finger_button_colors()
        
        finger_name = FINGER_MAPPING.get(finger_index, f"Ngón {finger_index}")
        logger.info(f"👆 Đã chọn ngón tay: {finger_name}")
    
    def update_finger_button_colors(self):
        """Cập nhật màu sắc cho finger buttons theo quy tắc enhanced"""
        if not self.main_app.selected_employee:
            # Reset all buttons to default
            for btn in self.finger_buttons.values():
                btn.configure(fg_color=("gray75", "gray25"))
            return
        
        employee_id = self.main_app.selected_employee.get('employee')
        fingerprint_data = self.main_app.current_fingerprints.get(employee_id, {})
        existing_fingers = {fp['finger_index'] for fp in fingerprint_data.get('fingerprints', [])}
        
        for finger_index, btn in self.finger_buttons.items():
            if finger_index == self.main_app.selected_finger_index:
                # Currently selected finger - blue với enhanced color
                btn.configure(fg_color=("#1f538d", "#14375e"))
            elif finger_index in existing_fingers:
                # Has fingerprint data - green với enhanced color
                btn.configure(fg_color=("#2d7d32", "#1b5e20"))
            else:
                # No data, not selected - default gray
                btn.configure(fg_color=("gray75", "gray25"))
    
    def update_employee_list(self):
        """Cập nhật danh sách nhân viên"""
        for item in self.employee_tree.get_children():
            self.employee_tree.delete(item)
        
        for emp in self.main_app.employees:
            self.employee_tree.insert("", "end", values=(
                emp.get('employee', ''),
                emp.get('employee_name', ''),
                emp.get('custom_group', ''),
                emp.get('attendance_device_id', '')
            ))
        
        logger.info(f"📋 Đã cập nhật danh sách {len(self.main_app.employees)} nhân viên")
    
    def update_connection_status(self, scanner_connected: bool, erpnext_connected: bool):
        """Cập nhật trạng thái kết nối trên buttons"""
        # Update scanner button
        if scanner_connected:
            self.scanner_btn.configure(text="📷 Scanner", fg_color="green")
        else:
            self.scanner_btn.configure(text="📷 Scanner", fg_color="red")
            
        # Update ERPNext button
        if erpnext_connected:
            self.erpnext_btn.configure(text="🌐 ERPNext", fg_color="green")
        else:
            self.erpnext_btn.configure(text="🌐 ERPNext", fg_color="red")
        
        # Update device connection button - matching the same color behavior
        devices_connected = any(status == 'connected' for status in self.main_app.device_status.values())
        if devices_connected:
            self.device_connection_btn.configure(text="🖥️ Máy chấm công", fg_color="green")
        else:
            self.device_connection_btn.configure(text="🖥️ Máy chấm công", fg_color="red")
        
        # Log status updates với enhanced messaging
        if scanner_connected and erpnext_connected:
            logger.info("✅ Tất cả kết nối đã sẵn sàng - Có thể thực hiện đầy đủ chức năng")
        elif scanner_connected:
            logger.info("⚠️ Chỉ Scanner được kết nối - Có thể quét vân tay nhưng không thể đồng bộ với ERPNext")
        elif erpnext_connected:
            logger.info("⚠️ Chỉ ERPNext được kết nối - Có thể quản lý dữ liệu nhưng không thể quét vân tay")
        else:
            logger.warning("❌ Chưa có kết nối nào - Vui lòng kết nối thiết bị để sử dụng")
    
    def update_fingerprint_display(self):
        """Cập nhật hiển thị vân tay (placeholder for future enhancement)"""
        # Update finger button colors when fingerprints change
        self.update_finger_button_colors()

    def on_finger_button_double_click(self, finger_index):
        """Xử lý sự kiện double click vào nút vân tay"""
        if not self.main_app.selected_employee:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn nhân viên trước!")
            return
            
        employee_id = self.main_app.selected_employee['employee']
        if employee_id not in self.main_app.current_fingerprints:
            return
            
        # Xác nhận xóa
        finger_name = FINGER_MAPPING.get(finger_index, f"Ngón {finger_index}")
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa vân tay {finger_name}?"):
            # Xóa vân tay
            fingerprints = self.main_app.current_fingerprints[employee_id]['fingerprints']
            self.main_app.current_fingerprints[employee_id]['fingerprints'] = [
                fp for fp in fingerprints if fp['finger_index'] != finger_index
            ]
            
            # Cập nhật UI
            self.update_finger_button_colors()
            logger.info(f"✅ Đã xóa vân tay {finger_name} của {employee_id}")
            
    def merge_fingerprints_data(self, fingerprints_from_machine):
        """
        Merge dữ liệu từ máy chấm công với employees.json vào all_fingerprints.json
        
        Args:
            fingerprints_from_machine: Dict dữ liệu vân tay từ máy chấm công
            
        Returns:
            int: Số lượng nhân viên sau khi merge
        """
        try:
            import os
            import json
            
            # Load employees data
            employees = []
            if os.path.exists("data/employees.json"):
                with open("data/employees.json", 'r', encoding='utf-8') as f:
                    employees = json.load(f)
                logger.info(f"✅ Đã load {len(employees)} nhân viên từ employees.json")
            else:
                logger.warning("⚠️ Không tìm thấy file employees.json")
            
            # Create dictionary of employees by ID for quick lookup
            employees_dict = {emp.get('employee'): emp for emp in employees}
            employees_by_device_id = {emp.get('attendance_device_id'): emp for emp in employees 
                                    if emp.get('attendance_device_id')}
            
            # Load existing fingerprints data (if any)
            current_fingerprints = []
            if os.path.exists("data/all_fingerprints.json"):
                with open("data/all_fingerprints.json", 'r', encoding='utf-8') as f:
                    current_fingerprints = json.load(f)
                logger.info(f"✅ Đã load {len(current_fingerprints)} nhân viên từ all_fingerprints.json")
            
            # Create dictionary of current fingerprints by employee ID
            current_fingerprints_dict = {fp.get('employee'): fp for fp in current_fingerprints}
            
            # Process and merge data
            merged_fingerprints = {}
            
            # First, add all current fingerprints to the merged data
            for fp in current_fingerprints:
                employee_id = fp.get('employee')
                if employee_id:
                    merged_fingerprints[employee_id] = fp
            
            # Next, process fingerprints from machine and merge
            for employee_id, fp_machine in fingerprints_from_machine.items():
                device_id = fp_machine.get('attendance_device_id')
                
                # Skip if no employee ID or device ID
                if not employee_id or not device_id:
                    continue
                
                # If employee exists in our records
                if employee_id in employees_dict:
                    emp_data = employees_dict[employee_id]
                    
                    # If we already have fingerprint data for this employee
                    if employee_id in merged_fingerprints:
                        # Get existing fingerprint data
                        existing_fp = merged_fingerprints[employee_id]
                        
                        # Update the consistent fields
                        existing_fp['attendance_device_id'] = device_id
                        existing_fp['name'] = emp_data.get('name', '')
                        existing_fp['employee_name'] = emp_data.get('employee_name', '')
                        
                        # Merge fingerprints arrays - replace with new data from machine
                        existing_fp['fingerprints'] = fp_machine.get('fingerprints', [])
                        
                        # Update password and privilege if they exist in the machine data
                        if 'password' in fp_machine:
                            existing_fp['password'] = fp_machine['password']
                        if 'privilege' in fp_machine:
                            existing_fp['privilege'] = fp_machine['privilege']
                        
                        logger.info(f"🔄 Updated existing fingerprint data for {employee_id}")
                        
                    else:
                        # Create new entry using machine data but ensure consistent fields
                        new_fp = fp_machine.copy()
                        new_fp['employee'] = employee_id
                        new_fp['name'] = emp_data.get('name', '')
                        new_fp['employee_name'] = emp_data.get('employee_name', '')
                        new_fp['attendance_device_id'] = device_id
                        
                        merged_fingerprints[employee_id] = new_fp
                        logger.info(f"➕ Added new fingerprint data for {employee_id}")
                else:
                    # Employee not in our records - just add the machine data as is
                    merged_fingerprints[employee_id] = fp_machine
                    logger.warning(f"⚠️ Employee {employee_id} not found in employees.json, added anyway")
            
            # Convert dictionary back to list for saving
            merged_fingerprints_list = list(merged_fingerprints.values())
            
            # Save the merged data
            with open("data/all_fingerprints.json", 'w', encoding='utf-8') as f:
                json.dump(merged_fingerprints_list, f, ensure_ascii=False, indent=4)
            
            logger.info(f"✅ Đã merge và lưu {len(merged_fingerprints_list)} nhân viên vào all_fingerprints.json")
            return len(merged_fingerprints_list)
            
        except Exception as e:
            logger.error(f"❌ Lỗi merge dữ liệu: {str(e)}")
            raise e
