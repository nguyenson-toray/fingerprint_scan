"""
Các dialog box cho ứng dụng
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from typing import List, Dict

class AttendanceIDDialog:
    """Dialog hiển thị danh sách nhân viên chưa có attendance_device_id"""
    
    def __init__(self, parent, employees_without_id: List[Dict]):
        self.parent = parent
        self.employees = employees_without_id
        self.result = False
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Gán ID máy chấm công")
        self.dialog.geometry("600x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"600x400+{x}+{y}")
        
        self.create_widgets()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def create_widgets(self):
        """Tạo các widget cho dialog"""
        # Title
        title_label = ctk.CTkLabel(
            self.dialog, 
            text="Các nhân viên chưa có ID máy chấm công",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(20, 10))
        
        # Message
        message_label = ctk.CTkLabel(
            self.dialog,
            text="Phần mềm sẽ tự động gán ID máy chấm công cho các nhân viên sau:",
            font=ctk.CTkFont(size=12)
        )
        message_label.pack(pady=(0, 10))
        
        # Employee list frame
        list_frame = ctk.CTkFrame(self.dialog)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Scrollable frame for employee list
        scrollable_frame = ctk.CTkScrollableFrame(list_frame)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Employee list
        for i, emp in enumerate(self.employees, 1):
            emp_text = f"{i}. {emp.get('employee', '')} - {emp.get('employee_name', '')}"
            emp_label = ctk.CTkLabel(scrollable_frame, text=emp_text, anchor="w")
            emp_label.pack(fill="x", pady=2)
        
        # Buttons
        button_frame = ctk.CTkFrame(self.dialog)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        cancel_btn = ctk.CTkButton(
            button_frame, 
            text="Hủy", 
            command=self.cancel,
            fg_color="gray"
        )
        cancel_btn.pack(side="left", padx=(10, 5), pady=10)
        
        ok_btn = ctk.CTkButton(
            button_frame, 
            text="OK - Gán ID tự động", 
            command=self.accept
        )
        ok_btn.pack(side="right", padx=(5, 10), pady=10)
    
    def accept(self):
        """Chấp nhận gán ID"""
        self.result = True
        self.dialog.destroy()
    
    def cancel(self):
        """Hủy gán ID"""
        self.result = False
        self.dialog.destroy()