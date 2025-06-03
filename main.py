# main.py
"""
Ứng dụng quản lý đăng ký vân tay cho nhân viên ERPNext HRMS
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import threading
import queue
from PIL import Image
import sys
import base64 # Import base64 for encoding/decoding

# Import các modules
from config import *
from fingerprint_scanner import FingerprintScanner
from erpnext_api import ERPNextAPI
from attendance_sync import AttendanceDeviceSync

# Thiết lập logging
def setup_logging():
    """Thiết lập logging cho ứng dụng"""
    # Tạo thư mục log nếu chưa có
    if not os.path.exists('log'):
        os.makedirs('log')
    
    # Tạo tên file log theo ngày
    log_filename = f"log/fingerprint_app_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Cấu hình logging
    logging.basicConfig(
        level=getattr(logging, LOG_CONFIG['log_level']),\
        format=LOG_CONFIG['log_format'],
        datefmt=LOG_CONFIG['date_format'],
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

# Setup logging
logger = setup_logging()

# Set theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class LogHandler(logging.Handler):
    """Custom log handler để hiển thị log trong GUI"""
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget
        
    def emit(self, record):
        msg = self.format(record)
        
        # Thêm icon và màu theo log level
        if record.levelname == 'ERROR':
            icon = "❌"
            tag = "error"
        elif record.levelname == 'WARNING':
            icon = "⚠️"
            tag = "warning"
        elif record.levelname == 'INFO':
            if "✅" in msg:
                icon = ""
                tag = "success"
            elif "🔍" in msg or "📷" in msg:
                icon = ""
                tag = "info"
            else:
                icon = "ℹ️"
                tag = "info"
        else:
            icon = "📝"
            tag = "debug"
        
        # Format message với timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {icon} {msg}\n"
        
        # Update UI trong main thread
        self.log_widget.after(0, self._update_log, formatted_msg, tag)
    
    def _update_log(self, msg, tag):
        self.log_widget.configure(state='normal')
        self.log_widget.insert('end', msg, tag)
        self.log_widget.configure(state='disabled')
        self.log_widget.see('end')


class FingerprintApp(ctk.CTk):
    """Lớp chính của ứng dụng"""
    
    def __init__(self):
        super().__init__()
        
        # Khởi tạo các biến
        self.scanner = FingerprintScanner()
        self.erpnext = ERPNextAPI()
        self.sync_manager = AttendanceDeviceSync(self.erpnext)
        
        # State variables
        self.current_employee = None
        self.current_fingerprints = {} # Stores fingerprints for the currently selected employee
        self.selected_finger = 0
        self.employees_list = [] # Full list of employees from ERPNext
        self.is_scanning = False
        
        # Change tracking
        self.has_unsaved_changes = False
        self.original_fingerprints = {} # Store original state for comparison
        
        # Queue cho background tasks
        self.task_queue = queue.Queue()
        
        # Setup GUI
        self.setup_window()
        self.create_widgets()
        
        # Bind events
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start background worker
        self.start_background_worker()
        
        logger.info("🚀 Ứng dụng đã khởi động")
        
    def setup_window(self):
        """Cấu hình cửa sổ chính"""
        self.title(UI_CONFIG['app_title'])
        self.geometry(f"{UI_CONFIG['window_width']}x{UI_CONFIG['window_height']}")
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (UI_CONFIG['window_width'] // 2)
        y = (self.winfo_screenheight() // 2) - (UI_CONFIG['window_height'] // 2)
        self.geometry(f"+{x}+{y}")
        
        # Set icon nếu có
        try:
            if os.path.exists('photos/logo.png'):
                logo_img = Image.open('photos/logo.png')
                logo_img = logo_img.resize((120, 40), Image.Resampling.LANCZOS)
                logo_ctk = ctk.CTkImage(logo_img, size=(120, 40))
                # Fix: logo_label needs to be packed into logo_frame, which is defined in create_top_section
                # This block is called before create_top_section, so logo_frame doesn't exist yet.
                # It's better to move logo loading to create_top_section.
                pass 
        except Exception as e:
            logger.error(f"❌ Lỗi tải logo (trong setup_window): {e}")
            pass
    
    def create_widgets(self):
        """Tạo giao diện người dùng"""
        # Main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create sections
        self.create_top_section()
        self.create_middle_section()
        
    def create_top_section(self):
        """Tạo phần hiển thị trạng thái"""
        self.top_frame = ctk.CTkFrame(self.main_container, height=60)
        self.top_frame.pack(fill='x', padx=5, pady=(5, 10))
        self.top_frame.pack_propagate(False)
        
        # Logo
        logo_frame = ctk.CTkFrame(self.top_frame)
        logo_frame.pack(side='left', padx=10)
        
        try:
            if os.path.exists('photos/logo.png'):
                logo_img = Image.open('photos/logo.png')
                logo_img = logo_img.resize((120, 30), Image.Resampling.LANCZOS)
                logo_ctk = ctk.CTkImage(logo_img, size=(120, 30))
                logo_label = ctk.CTkLabel(logo_frame, image=logo_ctk, text="")
                logo_label.pack()
            else:
                logger.warning("⚠️ Không tìm thấy file logo.png trong thư mục photos.")
        except Exception as e:
            logger.error(f"❌ Lỗi tải logo: {e}")
            pass
        
        # Status indicators
        status_frame = ctk.CTkFrame(self.top_frame)
        status_frame.pack(side='left', fill='x', expand=True, padx=20)
        
        # ERPNext status
        self.erpnext_status = ctk.CTkLabel(
            status_frame,
            text="ERPNext: ❌ Chưa kết nối",
            font=("Arial", 14)
        )
        self.erpnext_status.pack(side='left', padx=20)
        
        # Scanner status
        self.scanner_status = ctk.CTkLabel(
            status_frame,
            text="Scanner: ❌ Chưa kết nối",
            font=("Arial", 14)
        )
        self.scanner_status.pack(side='left', padx=20)
        
        # Progress
        self.progress_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=("Arial", 14)
        )
        self.progress_label.pack(side='left', padx=20)
        
    def create_middle_section(self):
        """Tạo phần chính của ứng dụng"""
        middle_frame = ctk.CTkFrame(self.main_container)
        middle_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left panel - Employee list
        self.create_employee_panel(middle_frame)
        
        # Center panel - Controls
        self.create_control_panel(middle_frame)
        
        # Right panel - Fingerprint & Log
        self.create_right_panel(middle_frame)
        
    def create_employee_panel(self, parent):
        """Tạo panel danh sách nhân viên"""
        left_frame = ctk.CTkFrame(parent, width=350)
        left_frame.pack(side='left', fill='both', expand=False, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        # Title
        title = ctk.CTkLabel(
            left_frame,
            text="📋 DANH SÁCH NHÂN VIÊN",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=10)
        
        # Search box
        search_frame = ctk.CTkFrame(left_frame)
        search_frame.pack(fill='x', padx=10, pady=5)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Tìm kiếm nhân viên..."
        )
        self.search_entry.pack(fill='x', padx=5, pady=5)
        self.search_entry.bind('<KeyRelease>', self.on_search)
        
        # Employee listbox with scrollbar
        list_frame = ctk.CTkFrame(left_frame)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Listbox
        self.employee_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 11),
            bg="#212121",
            fg="white",
            selectbackground="#1f538d",
            selectforeground="white",
            activestyle='none'
        )
        self.employee_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.configure(command=self.employee_listbox.yview)
        
        # Bind selection event
        self.employee_listbox.bind('<<ListboxSelect>>', self.on_employee_select)
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            left_frame,
            text="🔄 Làm mới danh sách",
            command=self.refresh_employee_list
        )
        refresh_btn.pack(pady=10)
        
    def create_control_panel(self, parent):
        """Tạo panel điều khiển"""
        center_frame = ctk.CTkFrame(parent, width=400)
        center_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        # Title
        title = ctk.CTkLabel(
            center_frame,
            text="🎛️ ĐIỀU KHIỂN",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=10)
        
        # Connection controls
        conn_frame = ctk.CTkFrame(center_frame)
        conn_frame.pack(fill='x', padx=20, pady=10)
        
        ctk.CTkLabel(
            conn_frame,
            text="Kết nối hệ thống:",
            font=("Arial", 14)
        ).pack(pady=5)
        
        btn_frame1 = ctk.CTkFrame(conn_frame)
        btn_frame1.pack(pady=5)
        
        self.connect_scanner_btn = ctk.CTkButton(
            btn_frame1,
            text="🔌 Kết nối Scanner",
            command=self.connect_scanner,
            width=180
        )
        self.connect_scanner_btn.pack(side='left', padx=5)
        
        self.connect_erpnext_btn = ctk.CTkButton(
            btn_frame1,
            text="🔌 Kết nối ERPNext",
            command=self.connect_erpnext,
            width=180
        )
        self.connect_erpnext_btn.pack(side='left', padx=5)
        
        # Separator
        ctk.CTkLabel(center_frame, text="", height=1).pack(fill='x', padx=20, pady=5)
        
        # Fingerprint controls
        fp_frame = ctk.CTkFrame(center_frame)
        fp_frame.pack(fill='x', padx=20, pady=10)
        
        ctk.CTkLabel(
            fp_frame,
            text="Quản lý vân tay:",
            font=("Arial", 14)
        ).pack(pady=5)
        
        # Current employee info
        self.current_emp_label = ctk.CTkLabel(
            fp_frame,
            text="Chưa chọn nhân viên",
            font=("Arial", 12),
            text_color="gray"
        )
        self.current_emp_label.pack(pady=5)
        
        btn_frame2 = ctk.CTkFrame(fp_frame)
        btn_frame2.pack(pady=5)
        
        self.add_fingerprint_btn = ctk.CTkButton(
            btn_frame2,
            text="➕ Thêm vân tay",
            command=self.add_fingerprint,
            width=180,
            state='disabled'
        )
        self.add_fingerprint_btn.pack(side='left', padx=5)
        
        self.delete_fingerprint_btn = ctk.CTkButton(
            btn_frame2,
            text="🗑️ Xóa vân tay",
            command=self.delete_fingerprint,
            width=180,
            state='disabled'
        )
        self.delete_fingerprint_btn.pack(side='left', padx=5)
        
        # Save button
        self.save_btn = ctk.CTkButton(
            fp_frame,
            text="💾 Lưu vân tay cục bộ", # Changed button text
            command=self.save_local_fingerprints, # Changed command name
            width=370,
            height=40,
            font=("Arial", 14, "bold"),
            state='disabled'
        )
        self.save_btn.pack(pady=10)

        # New button for auto-assigning attendance_device_id
        self.assign_id_btn = ctk.CTkButton(
            fp_frame,
            text="🔢 Gán ID máy CC tự động",
            command=self.assign_attendance_device_ids,
            width=370,
            height=40,
            font=("Arial", 14, "bold"),
            state='disabled' # Initially disabled, enable after ERPNext connection
        )
        self.assign_id_btn.pack(pady=10)
        
        # Separator
        ctk.CTkLabel(center_frame, text="", height=1).pack(fill='x', padx=20, pady=5)
        
        # Sync controls
        sync_frame = ctk.CTkFrame(center_frame)
        sync_frame.pack(fill='x', padx=20, pady=10)
        
        ctk.CTkLabel(
            sync_frame,
            text="Đồng bộ máy chấm công:",
            font=("Arial", 14)
        ).pack(pady=5)
        
        # Device selection
        self.device_var = tk.StringVar()
        self.device_combo = ctk.CTkComboBox(
            sync_frame,
            values=["Tất cả thiết bị"] + [d['name'] for d in ATTENDANCE_DEVICES],
            variable=self.device_var,
            width=370
        )
        self.device_combo.set("Tất cả thiết bị")
        self.device_combo.pack(pady=5)
        
        # Sync buttons
        btn_frame3 = ctk.CTkFrame(sync_frame)
        btn_frame3.pack(pady=5)
        
        self.sync_btn = ctk.CTkButton(
            btn_frame3,
            text="🔄 Đồng bộ",
            command=self.sync_to_devices,
            width=180,
            state='disabled'
        )
        self.sync_btn.pack(side='left', padx=5)
        
        self.view_devices_btn = ctk.CTkButton(
            btn_frame3,
            text="📱 Xem thiết bị",
            command=self.view_devices,
            width=180
        )
        self.view_devices_btn.pack(side='left', padx=5)
        
    def create_right_panel(self, parent):
        """Tạo panel bên phải với vân tay và log"""
        self.right_panel = ctk.CTkFrame(parent, width=400)
        self.right_panel.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # Fingerprint section
        fp_section = ctk.CTkFrame(self.right_panel, height=300)
        fp_section.pack(fill='x', padx=5, pady=5)
        fp_section.pack_propagate(False)
        
        ctk.CTkLabel(
            fp_section,
            text="👆 VÂN TAY",
            font=("Arial", 16, "bold")
        ).pack(pady=5)
        
        # Finger buttons container
        finger_container = ctk.CTkFrame(fp_section)
        finger_container.pack(fill='x', padx=10, pady=10)
        
        # Left and right hand frames
        left_hand_frame = ctk.CTkFrame(finger_container)
        left_hand_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        right_hand_frame = ctk.CTkFrame(finger_container)
        right_hand_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        # Labels for hands
        ctk.CTkLabel(
            left_hand_frame,
            text="Tay trái",
            font=("Arial", 12, "bold")
        ).pack(pady=5)
        
        ctk.CTkLabel(
            right_hand_frame,
            text="Tay phải",
            font=("Arial", 12, "bold")
        ).pack(pady=5)
        
        # Tạo các button cho từng ngón
        self.finger_buttons = {}
        finger_names = {
            5: "Ngón cái",
            6: "Ngón trỏ",
            7: "Ngón giữa",
            8: "Ngón nhẫn",
            9: "Ngón út",
            0: "Ngón cái",
            1: "Ngón trỏ",
            2: "Ngón giữa",
            3: "Ngón nhẫn",
            4: "Ngón út"
        }
        
        # Sắp xếp button theo tay trái và phải
        for finger_id, name in finger_names.items():
            # Chọn frame dựa vào finger_id
            frame = left_hand_frame if finger_id >= 5 else right_hand_frame
            
            # Tạo button
            btn = ctk.CTkButton(
                frame,
                text=name,
                width=100,
                height=40,
                command=lambda fid=finger_id: self.select_finger(fid)
            )
            btn.pack(pady=2)
            self.finger_buttons[finger_id] = btn
        
        # Selected finger info
        self.finger_info_label = ctk.CTkLabel(
            finger_container,
            text="Chọn một ngón tay",
            font=("Arial", 12)
        )
        self.finger_info_label.pack(pady=5)
        
        # Fingerprint list
        fp_list_frame = ctk.CTkFrame(fp_section)
        fp_list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(
            fp_list_frame,
            text="Danh sách vân tay đã có:",
            font=("Arial", 12)
        ).pack()
        
        self.fp_listbox = tk.Listbox(
            fp_list_frame,
            height=5,
            font=("Arial", 11),
            bg="#212121",
            fg="white",
            selectbackground="#1f538d"
        )
        self.fp_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Log section
        log_section = ctk.CTkFrame(self.right_panel)
        log_section.pack(fill='both', expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(
            log_section,
            text="📝 NHẬT KÝ",
            font=("Arial", 16, "bold")
        ).pack(pady=5)
        
        # Log text
        log_frame = ctk.CTkFrame(log_section)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(
            log_frame,
            wrap='word',
            font=("Consolas", 10),
            bg="#1a1a1a",
            fg="white",
            state='disabled'
        )
        self.log_text.pack(side='left', fill='both', expand=True)
        
        # Scrollbar for log
        log_scrollbar = ctk.CTkScrollbar(log_frame)
        log_scrollbar.pack(side='right', fill='y')
        log_scrollbar.configure(command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # Configure log tags
        self.log_text.tag_config('error', foreground='#ff4444')
        self.log_text.tag_config('warning', foreground='#ffaa00')
        self.log_text.tag_config('success', foreground='#44ff44')
        self.log_text.tag_config('info', foreground='#88ccff')
        self.log_text.tag_config('debug', foreground='#888888')
        
        # Add log handler
        log_handler = LogHandler(self.log_text)
        log_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(log_handler)
        
        # Clear log button
        clear_btn = ctk.CTkButton(
            log_section,
            text="🗑️ Xóa log",
            command=self.clear_log,
            width=100
        )
        clear_btn.pack(pady=5)
    
    def start_background_worker(self):
        """Khởi động worker thread cho các tác vụ nền"""
        def worker():
            while True:
                try:
                    task = self.task_queue.get()
                    if task is None:
                        break
                    
                    func, args, kwargs = task
                    func(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Lỗi trong background worker: {str(e)}")
                finally:
                    self.task_queue.task_done()
        
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
    
    def run_in_background(self, func, *args, **kwargs):
        """Chạy một hàm trong background"""
        self.task_queue.put((func, args, kwargs))
    
    # Event handlers
    def on_closing(self):
        """Xử lý khi đóng ứng dụng"""
        if messagebox.askokcancel("Xác nhận", "Bạn có chắc muốn thoát ứng dụng?"):
            logger.info("👋 Đang đóng ứng dụng...")
            
            # Cleanup
            if self.scanner.is_connected:
                self.scanner.disconnect()
            
            self.sync_manager.disconnect_all_devices()
            
            # Stop worker thread
            self.task_queue.put(None)
            
            self.destroy()
    
    def on_search(self, event):
        """Xử lý tìm kiếm nhân viên"""
        search_text = self.search_entry.get().lower()
        
        # Clear listbox
        self.employee_listbox.delete(0, tk.END)
        
        # Filter and display
        for emp in self.employees_list:
            display_text = f"{emp.get('attendance_device_id', 'N/A')} - {emp['employee']} - {emp['employee_name']}"
            
            if search_text in display_text.lower():
                self.employee_listbox.insert(tk.END, display_text)
    
    def on_employee_select(self, event):
        """Xử lý khi chọn nhân viên"""
        selection = self.employee_listbox.curselection()
        if not selection:
            return
        
        # Check for unsaved changes
        if self.has_unsaved_changes:
            if not messagebox.askyesno("Cảnh báo", "Bạn có thay đổi chưa lưu. Bạn có muốn lưu trước khi chuyển nhân viên?"):
                return
        
        # Get selected employee
        selected_text = self.employee_listbox.get(selection[0])
        employee_code = selected_text.split(' - ')[1]
        
        # Find employee data
        for emp in self.employees_list:
            if emp['employee'] == employee_code:
                self.current_employee = emp
                break
        
        if self.current_employee:
            # Update UI
            self.current_emp_label.configure(
                text=f"Nhân viên: {self.current_employee['employee']} - {self.current_employee['employee_name']}",
                text_color="white"
            )
            
            # Enable buttons
            self.add_fingerprint_btn.configure(state='normal')
            self.delete_fingerprint_btn.configure(state='normal')
            self.save_btn.configure(state='normal')
            
            # Load fingerprints and store original state
            self.load_employee_fingerprints()
            self.original_fingerprints = self.current_fingerprints.copy()
            self.has_unsaved_changes = False
    
    def select_finger(self, index):
        """Xử lý khi chọn ngón tay"""
        self.selected_finger = index
        
        # Update UI
        self.finger_info_label.configure(
            text=f"Ngón được chọn: {FINGER_MAPPING[index]}"
        )
        
        # Update button colors
        for i, btn in self.finger_buttons.items():
            if i == self.selected_finger: # Highlight selected finger
                btn.configure(fg_color="#1f538d")
            else:
                # Check if finger has data, if so, keep it green
                if i in self.current_fingerprints and self.current_fingerprints[i].get('template_data'):
                    btn.configure(fg_color="#2d7a2d")
                else:
                    btn.configure(fg_color="#3a3a3a")
    
    # Connection methods
    def connect_scanner(self):
        """Kết nối với scanner vân tay"""
        self.progress_label.configure(text="Đang kết nối scanner...")
        
        def task():
            if self.scanner.connect():
                self.after(0, lambda: self.scanner_status.configure(text="Scanner: ✅ Đã kết nối"))
                self.after(0, lambda: self.progress_label.configure(text=""))
            else:
                self.after(0, lambda: self.scanner_status.configure(text="Scanner: ❌ Lỗi kết nối"))
                self.after(0, lambda: self.progress_label.configure(text=""))
        
        self.run_in_background(task)
    
    def connect_erpnext(self):
        """Kết nối với ERPNext"""
        self.progress_label.configure(text="Đang kết nối ERPNext...")
        
        def task():
            if self.erpnext.test_connection():
                self.after(0, lambda: self.erpnext_status.configure(text="ERPNext: ✅ Đã kết nối"))
                self.after(0, lambda: self.sync_btn.configure(state='normal'))
                self.after(0, lambda: self.assign_id_btn.configure(state='normal')) # Enable assign ID button
                self.after(0, self.refresh_employee_list)
            else:
                self.after(0, lambda: self.erpnext_status.configure(text="ERPNext: ❌ Lỗi kết nối"))
            
            self.after(0, lambda: self.progress_label.configure(text=""))
        
        self.run_in_background(task)
    
    def refresh_employee_list(self):
        """Làm mới danh sách nhân viên"""
        self.progress_label.configure(text="Đang tải danh sách nhân viên...")
        
        def task():
            employees = self.erpnext.get_all_employees()
            self.employees_list = employees
            
            # Load existing fingerprints from local data file
            self.load_all_local_fingerprints()
            
            self.after(0, self._update_employee_list)
            self.after(0, lambda: self.progress_label.configure(text=""))
        
        self.run_in_background(task)
    
    def _update_employee_list(self):
        """Cập nhật danh sách nhân viên trong GUI"""
        self.employee_listbox.delete(0, tk.END)
        
        # Sort employees by 'employee' in descending order
        sorted_employees = sorted(self.employees_list, key=lambda x: x.get('employee', ''), reverse=True)

        for emp in sorted_employees:
            # Check if attendance_device_id exists and is not None/empty
            attendance_id = emp.get('attendance_device_id')
            if attendance_id is None or attendance_id == "":
                attendance_id_display = "N/A"
            else:
                attendance_id_display = str(attendance_id)

            display_text = f"{attendance_id_display} - {emp['employee']} - {emp['employee_name']}"
            self.employee_listbox.insert(tk.END, display_text)

        # Re-select current employee if still in the list
        if self.current_employee:
            for i, emp in enumerate(sorted_employees):
                if emp['employee'] == self.current_employee['employee']:
                    self.employee_listbox.selection_set(i)
                    self.employee_listbox.see(i)
                    break
        
    def load_all_local_fingerprints(self):
        """Tải tất cả dữ liệu vân tay từ thư mục data cục bộ (từ một file duy nhất)"""
        file_path = os.path.join('data', 'all_fingerprints.json')
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_fingerprint_data = json.load(f)
                
                logger.info(f"Loading fingerprints from {file_path}")
                
                # Create a mapping from employee_id to their fingerprint data for quick lookup
                fingerprint_map = {}
                for emp_data in all_fingerprint_data:
                    employee_id = emp_data['employee']
                    fingerprints = []
                    
                    for fp in emp_data.get('fingerprints', []):
                        try:
                            # Keep template_data as base64 string
                            if isinstance(fp.get('template_data'), str):
                                fingerprints.append({
                                    'finger_index': fp['finger_index'],
                                    'template_data': fp['template_data'],  # Keep as base64 string
                                    'quality_score': fp.get('quality_score', 0)
                                })
                                logger.info(f"Successfully loaded fingerprint {fp['finger_index']} for employee {employee_id}")
                        except Exception as e:
                            logger.error(f"Error loading fingerprint for {employee_id}: {e}")
                    
                    fingerprint_map[employee_id] = fingerprints
                    # logger.info(f"Loaded {len(fingerprints)} fingerprints for employee {employee_id}")

                # Update self.employees_list with fingerprint data
                for emp in self.employees_list:
                    emp_fingerprints = fingerprint_map.get(emp['employee'], [])
                    emp['fingerprints'] = emp_fingerprints
                    
                    # If this is the current employee, update current_fingerprints
                    if self.current_employee and emp['employee'] == self.current_employee['employee']:
                        self.current_fingerprints = {fp['finger_index']: fp for fp in emp_fingerprints}
                        logger.info(f"Updated current_fingerprints for {emp['employee']} with {len(emp_fingerprints)} fingerprints")
                
                logger.info("✅ Đã tải dữ liệu vân tay cục bộ cho tất cả nhân viên.")
                
            except Exception as e:
                logger.error(f"❌ Lỗi đọc file dữ liệu vân tay cục bộ: {e}")
        else:
            logger.info("ℹ️ Không tìm thấy file 'all_fingerprints.json'. Bắt đầu với dữ liệu vân tay trống.")

        return fingerprint_map

    def load_employee_fingerprints(self):
        """Tải dữ liệu vân tay của nhân viên hiện tại từ bộ nhớ cục bộ"""
        if not self.current_employee:
            return
        
        self.progress_label.configure(text="Đang tải dữ liệu vân tay...")
        
        # Get fingerprints from the current_employee object (which was loaded from local data)
        fingerprints = self.current_employee.get('fingerprints', [])
        
        # Update current fingerprints
        self.current_fingerprints = {}
        for fp in fingerprints:
            self.current_fingerprints[fp['finger_index']] = fp
        
        self.after(0, self._update_fingerprint_display)
        self.after(0, lambda: self.progress_label.configure(text=""))
        
    def _update_fingerprint_display(self):
        """Cập nhật hiển thị vân tay"""
        # Update finger buttons
        for i, btn in self.finger_buttons.items():
            if i == self.selected_finger: # Highlight selected finger
                btn.configure(fg_color="#1f538d")
            else:
                # Check if finger has data, if so, keep it green
                if i in self.current_fingerprints and self.current_fingerprints[i].get('template_data'):
                    btn.configure(fg_color="#2d7a2d")
                else:
                    btn.configure(fg_color="#3a3a3a")
        
        # Update fingerprint list
        self.fp_listbox.delete(0, tk.END)
        for finger_idx, fp_data in sorted(self.current_fingerprints.items()):
            if fp_data.get('template_data'): # Only display if template data exists
                self.fp_listbox.insert(
                    tk.END,
                    f"Ngón {finger_idx}: {FINGER_MAPPING[finger_idx]} - Chất lượng: {fp_data.get('quality_score', 0)}"
                )
        
        # Enable save button if there are changes (implicitly handled by on_employee_select)
        # if self.current_fingerprints:
        #     self.save_btn.configure(state='normal')
    
    def add_fingerprint(self):
        """Thêm vân tay mới"""
        if not self.current_employee:
            messagebox.showerror("Lỗi", "Vui lòng chọn nhân viên trước!")
            return
        
        if not self.scanner.is_connected:
            messagebox.showerror("Lỗi", "Scanner chưa được kết nối!")
            return
        
        if self.is_scanning:
            messagebox.showwarning("Cảnh báo", "Đang quét vân tay, vui lòng đợi...")
            return
        
        self.is_scanning = True
        self.progress_label.configure(text=f"Đang quét vân tay ngón {self.selected_finger} ({FINGER_MAPPING[self.selected_finger]})...")
        
        def task():
            try:
                # Enroll fingerprint
                template = self.scanner.enroll_fingerprint(self.selected_finger)
                
                if template:
                    # Assign a default quality score
                    quality_score = FINGERPRINT_CONFIG.get('quality_threshold', 80)
                    
                    logger.info(f"Successfully enrolled fingerprint for finger {self.selected_finger}")
                    logger.info(f"Template type: {type(template)}")
                    
                    # Convert template to base64 for storage
                    try:
                        # Handle different types of template data
                        if isinstance(template, bytes):
                            template_b64 = base64.b64encode(template).decode('utf-8')
                        elif str(type(template)) == "<class 'System.Byte[]'>":
                            # Convert System.Byte[] to bytes
                            template_bytes = bytes(template)
                            template_b64 = base64.b64encode(template_bytes).decode('utf-8')
                        else:
                            logger.error(f"Unexpected template type: {type(template)}")
                            raise ValueError(f"Unsupported template type: {type(template)}")
                        
                        # Save to memory (current_fingerprints dict)
                        self.current_fingerprints[self.selected_finger] = {
                            'finger_index': self.selected_finger,
                            'template_data': template_b64,  # Store as base64 string
                            'quality_score': quality_score
                        }
                        
                        # Update the current_employee's fingerprints list
                        self.current_employee['fingerprints'] = list(self.current_fingerprints.values())
                        
                        # Update the employee in employees_list
                        for i, emp in enumerate(self.employees_list):
                            if emp['employee'] == self.current_employee['employee']:
                                self.employees_list[i] = self.current_employee
                                break
                        
                        # Mark as changed
                        self.has_unsaved_changes = True
                        self.save_btn.configure(text="💾 Lưu vân tay cục bộ (Có thay đổi)")
                        
                        
                        logger.info(f"Updated fingerprints for employee {self.current_employee['employee']}")
                        logger.info(f"Current fingerprints count: {len(self.current_fingerprints)}")
                        
                        self.after(0, self._update_fingerprint_display)
                        self.after(0, lambda: messagebox.showinfo("Thành công", "Đã thêm vân tay thành công! Vui lòng lưu lại để áp dụng thay đổi."))
                    except Exception as e:
                        logger.error(f"Error converting template data: {str(e)}")
                        self.after(0, lambda: messagebox.showerror("Lỗi", f"Không thể xử lý dữ liệu vân tay: {e}"))
                else:
                    logger.error("Failed to enroll fingerprint")
                    self.after(0, lambda: messagebox.showerror("Lỗi", "Không thể quét vân tay!"))
            except Exception as e:
                logger.error(f"Error in add_fingerprint: {str(e)}")
                self.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi không xác định: {e}"))
            finally:
                self.is_scanning = False
                self.after(0, lambda: self.progress_label.configure(text=""))
        
        self.run_in_background(task)
    
    def delete_fingerprint(self):
        """Xóa vân tay"""
        if not self.current_employee:
            messagebox.showerror("Lỗi", "Vui lòng chọn nhân viên trước!")
            return
        
        if self.selected_finger not in self.current_fingerprints:
            messagebox.showwarning("Cảnh báo", "Ngón tay này chưa có dữ liệu!")
            return
        
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa vân tay ngón {self.selected_finger} ({FINGER_MAPPING[self.selected_finger]})?"):
            self.progress_label.configure(text="Đang xóa vân tay...")
            
            # Remove from current_fingerprints in memory
            if self.selected_finger in self.current_fingerprints:
                del self.current_fingerprints[self.selected_finger]
                
                # Update the current_employee's fingerprints list
                self.current_employee['fingerprints'] = list(self.current_fingerprints.values())
                
                # Update the employee in employees_list
                for i, emp in enumerate(self.employees_list):
                    if emp['employee'] == self.current_employee['employee']:
                        self.employees_list[i] = self.current_employee
                        break
                
                # Mark as changed
                self.has_unsaved_changes = True
                self.save_btn.configure(text="💾 Lưu vân tay cục bộ (Có thay đổi)")

                self.after(0, self._update_fingerprint_display)
                self.after(0, lambda: messagebox.showinfo("Thành công", "Đã xóa vân tay khỏi bộ nhớ cục bộ! Vui lòng lưu lại để áp dụng thay đổi."))
            else:
                self.after(0, lambda: messagebox.showwarning("Cảnh báo", "Không tìm thấy vân tay để xóa trong bộ nhớ cục bộ."))
            
            self.after(0, lambda: self.progress_label.configure(text=""))
    
    def save_local_fingerprints(self):
        """Lưu dữ liệu vân tay của TẤT CẢ nhân viên vào một file JSON cục bộ duy nhất"""
        if not self.has_unsaved_changes:
            messagebox.showinfo("Thông báo", "Không có thay đổi nào để lưu!")
            return
            
        self.progress_label.configure(text="Đang lưu dữ liệu vân tay cục bộ...")
        
        def task():
            try:
                # Create data directory if it doesn't exist
                os.makedirs('data', exist_ok=True)
                
                # Load existing data first
                file_path = os.path.join('data', 'all_fingerprints.json')
                existing_data = []
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                
                # Create a mapping of existing data
                existing_map = {emp['employee']: emp for emp in existing_data}
                
                # Update only changed employees
                for emp in self.employees_list:
                    if emp['employee'] in existing_map:
                        # Update existing employee data
                        existing_map[emp['employee']].update({
                            'name': emp['name'],
                            'employee_name': emp['employee_name'],
                            'attendance_device_id': emp['attendance_device_id'],
                            'fingerprints': emp.get('fingerprints', [])
                        })
                    else:
                        # Add new employee
                        existing_map[emp['employee']] = {
                            'name': emp['name'],
                            'employee': emp['employee'],
                            'employee_name': emp['employee_name'],
                            'attendance_device_id': emp['attendance_device_id'],
                            'fingerprints': emp.get('fingerprints', [])
                        }
                
                # Convert back to list
                all_employee_data_to_save = list(existing_map.values())
                
                # Save to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(all_employee_data_to_save, f, ensure_ascii=False, indent=4)
                
                logger.info(f"✅ Đã lưu dữ liệu vân tay của tất cả nhân viên vào file cục bộ: {file_path}")
                
                # Reset change tracking
                self.has_unsaved_changes = False
                self.save_btn.configure(text="💾 Lưu vân tay cục bộ")
                self.original_fingerprints = self.current_fingerprints.copy()
                
                self.after(0, lambda: messagebox.showinfo("Thành công", "Đã lưu dữ liệu vân tay của tất cả nhân viên vào file cục bộ!"))
                
                # After saving, reload all local fingerprints to ensure in-memory data is consistent
                self.after(0, self.load_all_local_fingerprints)
                self.after(0, self.load_employee_fingerprints)
                self.after(0, self._update_employee_list)

            except Exception as e:
                logger.error(f"❌ Lỗi khi lưu dữ liệu vân tay cục bộ: {str(e)}")
                self.after(0, lambda: messagebox.showerror("Lỗi", f"Không thể lưu dữ liệu vào file cục bộ: {e}"))
            
            self.after(0, lambda: self.progress_label.configure(text=""))
        
        self.run_in_background(task)

    def assign_attendance_device_ids(self):
        """
        Tự động gán attendance_device_id tăng dần cho các nhân viên có ID null hoặc trống.
        Sau đó, đồng bộ các ID này lên ERPNext.
        """
        if not self.erpnext.is_connected:
            messagebox.showerror("Lỗi", "ERPNext chưa được kết nối!")
            return

        if not messagebox.askyesno("Xác nhận", "Bạn có chắc muốn tự động gán ID máy chấm công và đồng bộ lên ERPNext?"):
            return

        self.progress_label.configure(text="Đang gán ID máy chấm công...")

        def task():
            try:
                # Get current max attendance_device_id
                max_id = 0
                for emp in self.employees_list:
                    try:
                        if emp.get('attendance_device_id'):
                            current_id = int(emp['attendance_device_id'])
                            if current_id > max_id:
                                max_id = current_id
                    except ValueError:
                        continue # Ignore invalid IDs

                next_id = max_id + 1
                updated_count = 0
                
                employees_to_update_erpnext = []
                updated_employee_names_for_msg = [] # For the message box

                for emp in self.employees_list:
                    if not emp.get('attendance_device_id') or str(emp['attendance_device_id']).strip() == "":
                        # Assign new ID
                        emp['attendance_device_id'] = str(next_id)
                        employees_to_update_erpnext.append(emp)
                        updated_employee_names_for_msg.append(f"{emp['employee']} - {emp['employee_name']}")
                        next_id += 1
                        updated_count += 1
                        logger.info(f"Đã gán ID {emp['attendance_device_id']} cho {emp['employee_name']}")

                if updated_count > 0:
                    # Sync updated IDs to ERPNext
                    sync_success_count = 0
                    for emp_to_update in employees_to_update_erpnext:
                        if self.erpnext.update_employee_attendance_device_id(emp_to_update['name'], int(emp_to_update['attendance_device_id'])):
                            sync_success_count += 1
                    
                    self.after(0, self.refresh_employee_list) # Refresh list to show new IDs
                    
                    # Construct detailed message
                    detail_msg = "\n".join(updated_employee_names_for_msg)
                    final_msg = f"Đã gán và đồng bộ {updated_count} ID máy chấm công mới lên ERPNext.\n" \
                                f"Thành công {sync_success_count}/{updated_count} bản ghi.\n\n" \
                                f"Danh sách nhân viên được cập nhật:\n{detail_msg}"

                    self.after(0, lambda: messagebox.showinfo(
                        "Thành công",
                        final_msg
                    ))
                else:
                    self.after(0, lambda: messagebox.showinfo("Thông báo", "Không có nhân viên nào cần gán ID máy chấm công mới."))

            except Exception as e:
                logger.error(f"❌ Lỗi khi gán ID máy chấm công tự động: {str(e)}")
                self.after(0, lambda: messagebox.showerror("Lỗi", f"Không thể gán ID máy chấm công tự động: {e}"))
            finally:
                self.after(0, lambda: self.progress_label.configure(text=""))
        
        self.run_in_background(task)
    
    def sync_to_devices(self):
        """Đồng bộ vân tay đến các máy chấm công"""
        if not self.current_employee:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn nhân viên trước khi đồng bộ")
            return
            
        if not self.current_fingerprints:
            messagebox.showwarning("Cảnh báo", "Nhân viên chưa có dữ liệu vân tay")
            return
            
        # Kiểm tra attendance_device_id
        if not self.current_employee.get('attendance_device_id'):
            messagebox.showwarning("Cảnh báo", "Nhân viên chưa được gán ID máy chấm công")
            return
            
        # Xác nhận đồng bộ
        if not messagebox.askyesno("Xác nhận", 
            f"Bạn có chắc muốn đồng bộ vân tay của {self.current_employee['employee_name']} đến các máy chấm công?"):
            return
            
        def task():
            try:
                # Chuẩn bị dữ liệu
                employee_data = {
                    'employee': self.current_employee['employee'],
                    'employee_name': self.current_employee['employee_name'],
                    'attendance_device_id': self.current_employee['attendance_device_id']
                }
                
                # Chuyển đổi current_fingerprints thành list
                fingerprints = []
                for finger_index, fp_data in self.current_fingerprints.items():
                    if fp_data.get('template_data'):
                        fingerprints.append({
                            'finger_index': finger_index,
                            'template_data': fp_data['template_data'],
                            'quality_score': fp_data.get('quality_score', 0)
                        })
                
                if not fingerprints:
                    logger.warning("⚠️ Không có vân tay hợp lệ để đồng bộ")
                    return
                    
                # Thêm fingerprints vào employee_data
                employee_data['fingerprints'] = fingerprints
                
                # Đồng bộ đến từng thiết bị
                results = self.sync_manager.sync_to_all_devices([employee_data])
                
                # Hiển thị kết quả
                success_count = sum(1 for r in results.values() if r[0] > 0)
                total_devices = len(results)
                
                if success_count == total_devices:
                    messagebox.showinfo("Thành công", 
                        f"Đã đồng bộ thành công đến {success_count}/{total_devices} thiết bị")
                else:
                    messagebox.showwarning("Cảnh báo",
                        f"Đồng bộ thành công đến {success_count}/{total_devices} thiết bị")
                    
            except Exception as e:
                logger.error(f"❌ Lỗi đồng bộ: {str(e)}")
                messagebox.showerror("Lỗi", f"Lỗi đồng bộ: {str(e)}")
                
        # Chạy trong background
        self.run_in_background(task)
    
    def view_devices(self):
        """Xem thông tin các thiết bị"""
        devices_window = ctk.CTkToplevel(self)
        devices_window.title("Thông tin thiết bị")
        devices_window.geometry("800x600")
        
        # Create treeview
        tree = ttk.Treeview(
            devices_window,
            columns=('IP', 'Port', 'Model', 'Location'),
            show='headings' # Changed from 'tree headings' to 'headings' for cleaner display
        )
        
        # Define columns
        tree.heading('#1', text='Địa chỉ IP') # Changed from #0 to #1
        tree.heading('#2', text='Port')
        tree.heading('#3', text='Model')
        tree.heading('#4', text='Vị trí')

        # Set column widths
        tree.column('#1', width=100, anchor='center')
        tree.column('#2', width=70, anchor='center')
        tree.column('#3', width=150, anchor='center')
        tree.column('#4', width=200, anchor='w')
        
        # Add a column for device name (hidden, used for selection)
        tree["displaycolumns"] = ('IP', 'Port', 'Model', 'Location')
        
        # Add devices
        for device in ATTENDANCE_DEVICES:
            tree.insert('', 'end',
                       values=(device['ip'], device['port'], device['model'], device['location']),
                       text=device['name']) # Store device name in text for easy retrieval
        
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Test connection button
        def test_connection():
            selection = tree.selection()
            if selection:
                # Get the device name from the 'text' property of the selected item
                device_name = tree.item(selection[0], 'text')
                # Find device config
                for device in ATTENDANCE_DEVICES:
                    if device['name'] == device_name:
                        self.progress_label.configure(text=f"Đang kiểm tra {device_name}...")
                        
                        def task():
                            zk = self.sync_manager.connect_device(device)
                            if zk:
                                self.sync_manager.disconnect_device(device['id'])
                                self.after(0, lambda: messagebox.showinfo(
                                    "Thành công",
                                    f"Kết nối với {device_name} thành công!"
                                ))
                            else:
                                self.after(0, lambda: messagebox.showerror(
                                    "Lỗi",
                                    f"Không thể kết nối với {device_name}!"
                                ))
                            
                            self.after(0, lambda: self.progress_label.configure(text=""))
                        
                        self.run_in_background(task)
                        break
        
        test_btn = ctk.CTkButton(
            devices_window,
            text="🔌 Kiểm tra kết nối",
            command=test_connection
        )
        test_btn.pack(pady=10)
    
    def clear_log(self):
        """Xóa log hiển thị"""
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')


def main():
    """Hàm chính của ứng dụng"""
    # Create data directory if not exists
    os.makedirs('data', exist_ok=True)
    os.makedirs('log', exist_ok=True)
    os.makedirs('photos', exist_ok=True)
    
    # Run app
    app = FingerprintApp()
    app.mainloop()


if __name__ == "__main__":
    main()
