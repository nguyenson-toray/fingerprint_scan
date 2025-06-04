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
        self.save_btn.pack(side="right", padx=(5, 10), pady=5)
        
        # Enhanced sync section với device status display
        self.create_device_sync_section(parent)
    
    def create_device_sync_section(self, parent):
        """Tạo section đồng bộ máy chấm công với device status"""
        sync_frame = ctk.CTkFrame(parent)
        sync_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(sync_frame, text="🔄 Đồng bộ máy chấm công", 
                   font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Device connection button ở trên
        self.device_connection_btn = ctk.CTkButton(
            sync_frame,
            text="🖥️ Kết nối máy chấm công",
            command=self.connect_attendance_devices,
            width=250
        )
        self.device_connection_btn.pack(pady=(5, 10))
        
        # Sync button ngay phía dưới
        self.sync_btn = ctk.CTkButton(sync_frame, text="📤 Đồng bộ", 
                                    command=self.sync_to_selected_devices,
                                    width=250)
        self.sync_btn.pack(pady=(0, 10))
        
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
        
        # Sync button
        self.sync_btn = ctk.CTkButton(sync_frame, text="📤 Đồng bộ", 
                                    command=self.sync_to_selected_devices)
        self.sync_btn.pack(pady=5, padx=10)
    
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
            
            # Checkbox
            var = ctk.BooleanVar()
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
        self.erpnext_btn.pack(side="right", padx=5)
        
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
                        self.update_employee_list()
                        self.refresh_employee_btn.configure(text="🔄 Làm mới", state="normal")
                        messagebox.showinfo("Thành công", f"Đã cập nhật {len(new_employees)} nhân viên!")
                        logger.info(f"✅ Đã làm mới danh sách {len(new_employees)} nhân viên")
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