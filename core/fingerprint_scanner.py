# fingerprint_scanner.py
"""
Module xử lý quét vân tay sử dụng libzkfp.dll trực tiếp
"""

import logging
import ctypes
import time
from typing import Optional, List
from config import SCANNER_CONFIG, FINGERPRINT_CONFIG

logger = logging.getLogger(__name__)


class TZKFPCapParams(ctypes.Structure):
    """Cấu trúc tham số quét vân tay"""
    _fields_ = [
        ("imgWidth", ctypes.c_uint),
        ("imgHeight", ctypes.c_uint),
        ("nDPI", ctypes.c_uint)
    ]


class FingerprintScanner:
    """Lớp quản lý kết nối và quét vân tay sử dụng libzkfp.dll"""
    
    def __init__(self):
        self.zkfp = None
        self.handle = None
        self.hDBCache = None
        self.is_connected = False
        self.img_width = 0
        self.img_height = 0
        self.template_buf_size = 2048
        self.merge_count = FINGERPRINT_CONFIG.get('scan_count', 3)
        self.quality_threshold = FINGERPRINT_CONFIG.get('quality_threshold', 50)
        logger.info("FingerprintScanner đã được khởi tạo.")
        
    def connect(self) -> bool:
        """Kết nối với thiết bị scanner vân tay"""
        if self.is_connected:
            logger.info("Scanner đã được kết nối.")
            return True

        try:
            # Load DLL
            try:
                self.zkfp = ctypes.windll.LoadLibrary("libzkfp.dll")
            except Exception as e:
                logger.error(f"❌ Không thể load libzkfp.dll: {e}")
                return False
            
            # Khai báo hàm
            self._declare_functions()
            
            # Khởi tạo SDK
            if self.zkfp.ZKFPM_Init() != 0:
                logger.error("❌ Không thể khởi tạo SDK máy quét vân tay.")
                return False
            
            # Kiểm tra số thiết bị
            device_count = self.zkfp.ZKFPM_GetDeviceCount()
            if device_count == 0:
                logger.error("❌ Không tìm thấy thiết bị quét vân tay nào.")
                self.zkfp.ZKFPM_Terminate()
                return False
            
            # Mở thiết bị đầu tiên
            self.handle = self.zkfp.ZKFPM_OpenDevice(0)
            if not self.handle:
                logger.error("❌ Không thể mở thiết bị quét.")
                self.zkfp.ZKFPM_Terminate()
                return False
            
            # Lấy thông số thiết bị
            params = TZKFPCapParams()
            if self.zkfp.ZKFPM_GetCaptureParams(self.handle, ctypes.byref(params)) == 0:
                self.img_width = params.imgWidth
                self.img_height = params.imgHeight
                logger.info(f"📷 Kích thước ảnh: {self.img_width}x{self.img_height}, DPI: {params.nDPI}")
            
            # Khởi tạo DB Cache cho merge
            self.hDBCache = self.zkfp.ZKFPM_DBInit()
            if not self.hDBCache:
                logger.error("❌ Không thể khởi tạo bộ đệm DB để merge vân tay.")
                self.zkfp.ZKFPM_CloseDevice(self.handle)
                self.zkfp.ZKFPM_Terminate()
                return False
            
            self.is_connected = True
            logger.info(f"✅ Đã kết nối thành công với thiết bị quét vân tay (tìm thấy {device_count} thiết bị).")
            return True
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi khởi tạo hoặc kết nối scanner: {e}")
            self._cleanup()
            return False
    
    def _declare_functions(self):
        """Khai báo các hàm DLL"""
        # Hàm cơ bản
        self.zkfp.ZKFPM_Init.restype = ctypes.c_int
        self.zkfp.ZKFPM_Terminate.restype = ctypes.c_int
        self.zkfp.ZKFPM_GetDeviceCount.restype = ctypes.c_int
        
        self.zkfp.ZKFPM_OpenDevice.argtypes = [ctypes.c_int]
        self.zkfp.ZKFPM_OpenDevice.restype = ctypes.c_void_p
        
        self.zkfp.ZKFPM_CloseDevice.argtypes = [ctypes.c_void_p]
        self.zkfp.ZKFPM_CloseDevice.restype = ctypes.c_int
        
        self.zkfp.ZKFPM_GetCaptureParams.argtypes = [ctypes.c_void_p, ctypes.POINTER(TZKFPCapParams)]
        self.zkfp.ZKFPM_GetCaptureParams.restype = ctypes.c_int
        
        self.zkfp.ZKFPM_AcquireFingerprint.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.POINTER(ctypes.c_uint)
        ]
        self.zkfp.ZKFPM_AcquireFingerprint.restype = ctypes.c_int
        
        # Hàm merge
        self.zkfp.ZKFPM_DBInit.restype = ctypes.c_void_p
        
        self.zkfp.ZKFPM_DBMerge.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.POINTER(ctypes.c_uint)
        ]
        self.zkfp.ZKFPM_DBMerge.restype = ctypes.c_int
        
        self.zkfp.ZKFPM_DBFree.argtypes = [ctypes.c_void_p]
        self.zkfp.ZKFPM_DBFree.restype = ctypes.c_int
    
    def disconnect(self):
        """Ngắt kết nối thiết bị scanner"""
        if self.is_connected:
            try:
                self._cleanup()
                self.is_connected = False
                logger.info("✅ Đã ngắt kết nối scanner thành công.")
                return True
            except Exception as e:
                logger.error(f"❌ Lỗi khi ngắt kết nối scanner: {e}")
                return False
        else:
            logger.info("Scanner không được kết nối.")
            return True
    
    def _cleanup(self):
        """Dọn dẹp tài nguyên"""
        if self.hDBCache:
            self.zkfp.ZKFPM_DBFree(self.hDBCache)
            self.hDBCache = None
            
        if self.handle:
            self.zkfp.ZKFPM_CloseDevice(self.handle)
            self.handle = None
            
        if self.zkfp:
            self.zkfp.ZKFPM_Terminate()
    
    def get_device_info(self) -> str:
        """Lấy thông tin thiết bị scanner"""
        if not self.is_connected:
            return "Chưa kết nối"
            
        try:
            return f"{SCANNER_CONFIG['model']} - USB Connected ({self.img_width}x{self.img_height})"
        except:
            return SCANNER_CONFIG['model']
    
    def capture_fingerprint(self, finger_index: int, scan_number: int = 1) -> Optional[bytes]:
        """
        Quét vân tay một lần.
        Args:
            finger_index: Chỉ số ngón tay (0-9).
            scan_number: Lần quét thứ mấy (1-3).
        Returns:
            Template data nếu chụp thành công, None nếu thất bại.
        """
        if not self.is_connected or not self.zkfp or not self.handle:
            logger.error("❌ Scanner chưa được kết nối.")
            return None
            
        try:
            logger.info(f"🔍 Đang chờ quét vân tay lần {scan_number}/{self.merge_count}...")
            
            # Tạo buffer
            image_buf = (ctypes.c_ubyte * (self.img_width * self.img_height))()
            template_buf = (ctypes.c_ubyte * self.template_buf_size)()
            template_len = ctypes.c_uint(self.template_buf_size)
            
            start_time = time.time()
            timeout = SCANNER_CONFIG.get('timeout', 30)
            
            # Hiển thị thông báo rõ ràng hơn
            logger.info(f"👆 Vui lòng đặt ngón tay lên máy quét (lần {scan_number}/{self.merge_count})")
            
            while time.time() - start_time < timeout:
                ret = self.zkfp.ZKFPM_AcquireFingerprint(
                    self.handle,
                    image_buf,
                    self.img_width * self.img_height,
                    template_buf,
                    ctypes.byref(template_len)
                )
                
                if ret == 0:
                    template_data = bytes(template_buf[:template_len.value])
                    logger.info(f"✅ Đã chụp vân tay lần {scan_number} thành công.")
                    return template_data
                    
                time.sleep(0.1)
                
            logger.error(f"❌ Hết thời gian chờ quét vân tay lần {scan_number}.")
            return None
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi quét vân tay: {str(e)}")
            return None
    
    def enroll_fingerprint(self, finger_index: int) -> Optional[bytes]:
        """
        Đăng ký vân tay mới (quét 3 lần và merge).
        Args:
            finger_index: Chỉ số ngón tay (0-9).
        Returns:
            Dữ liệu template vân tay đã merge nếu thành công, None nếu thất bại.
        """
        if not self.is_connected or not self.zkfp or not self.handle:
            logger.error("❌ Scanner chưa được kết nối.")
            return None
            
        if not self.hDBCache:
            logger.error("❌ DB Cache chưa được khởi tạo.")
            return None
            
        collected_templates = []
        
        # Thu thập 3 mẫu vân tay
        for i in range(self.merge_count):
            logger.info(f"📷 Quét lần {i+1}/{self.merge_count}")
            
            template = self.capture_fingerprint(finger_index, i+1)
            if not template:
                logger.error(f"❌ Quét lần {i+1} thất bại")
                return None
            
            collected_templates.append(template)
            
            if i < self.merge_count - 1:
                logger.info("👆 Vui lòng nhấc ngón tay và đặt lại")
                time.sleep(2)
        
        # Merge 3 template
        try:
            logger.info("🔄 Đang merge 3 mẫu vân tay...")
            
            # Tạo buffer cho kết quả merge
            merged_template_buf = (ctypes.c_ubyte * self.template_buf_size)()
            merged_template_len = ctypes.c_uint(self.template_buf_size)
            
            # Chuyển đổi template thành ctypes array
            t1_c = (ctypes.c_ubyte * len(collected_templates[0]))(*collected_templates[0])
            t2_c = (ctypes.c_ubyte * len(collected_templates[1]))(*collected_templates[1])
            t3_c = (ctypes.c_ubyte * len(collected_templates[2]))(*collected_templates[2])
            
            # Thực hiện merge
            ret_merge = self.zkfp.ZKFPM_DBMerge(
                self.hDBCache,
                t1_c,
                t2_c,
                t3_c,
                merged_template_buf,
                ctypes.byref(merged_template_len)
            )
            
            if ret_merge == 0:
                final_template_data = bytes(merged_template_buf[:merged_template_len.value])
                logger.info(f"✅ Merge vân tay thành công! Kích thước template: {len(final_template_data)} bytes.")
                return final_template_data
            else:
                logger.error(f"❌ Lỗi khi merge vân tay. Mã lỗi: {ret_merge}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi merge vân tay: {str(e)}")
            return None
    
    def verify_fingerprint(self, template_data, finger_index):
        """
        Verify a fingerprint against a template
        Chức năng này có thể được implement sau nếu cần
        """
        logger.warning("⚠️ Chức năng verify_fingerprint chưa được implement với libzkfp.dll")
        return False
    
    def identify_fingerprint(self, templates_list: List) -> Optional[str]:
        """
        Nhận dạng vân tay từ danh sách template
        Chức năng này có thể được implement sau nếu cần
        """
        logger.warning("⚠️ Chức năng identify_fingerprint chưa được implement với libzkfp.dll")
        return None