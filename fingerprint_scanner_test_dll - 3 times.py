import ctypes
import time
from zk import ZK, const
from zk.base import Finger

# ==== CẤU HÌNH ====
DEVICE_IP = "10.0.1.48"
USER_ID = "2226"  # kiểu string nhưng pyzk yêu cầu uid là int, sẽ chuyển xuống
FINGER_ID = 0 # Finger ID to save (0-9)

# ==== CẤU TRÚC SDK ====
class TZKFPCapParams(ctypes.Structure):
    _fields_ = [
        ("imgWidth", ctypes.c_uint),
        ("imgHeight", ctypes.c_uint),
        ("nDPI", ctypes.c_uint)
    ]

# ==== LOAD DLL ====
zkfp = ctypes.windll.LoadLibrary("libzkfp.dll")

# KHAI BÁO HÀM
zkfp.ZKFPM_Init.restype = ctypes.c_int
zkfp.ZKFPM_Terminate.restype = ctypes.c_int
zkfp.ZKFPM_GetDeviceCount.restype = ctypes.c_int
zkfp.ZKFPM_OpenDevice.argtypes = [ctypes.c_int]
zkfp.ZKFPM_OpenDevice.restype = ctypes.c_void_p
zkfp.ZKFPM_CloseDevice.argtypes = [ctypes.c_void_p]
zkfp.ZKFPM_CloseDevice.restype = ctypes.c_int
zkfp.ZKFPM_GetCaptureParams.argtypes = [ctypes.c_void_p, ctypes.POINTER(TZKFPCapParams)]
zkfp.ZKFPM_GetCaptureParams.restype = ctypes.c_int
zkfp.ZKFPM_AcquireFingerprint.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.c_uint,
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.POINTER(ctypes.c_uint)
]
zkfp.ZKFPM_AcquireFingerprint.restype = ctypes.c_int

# ==== ADDED FOR MERGING FUNCTIONS ====
# Declare ZKFPM_DBInit to create the algorithm operation instance
zkfp.ZKFPM_DBInit.restype = ctypes.c_void_p # It returns a HANDLE (void_p)
# Declare ZKFPM_DBMerge (or ZKFPM_GenRegTemplate)
zkfp.ZKFPM_DBMerge.argtypes = [
    ctypes.c_void_p,            # hDBCache
    ctypes.POINTER(ctypes.c_ubyte), # temp1
    ctypes.POINTER(ctypes.c_ubyte), # temp2
    ctypes.POINTER(ctypes.c_ubyte), # temp3
    ctypes.POINTER(ctypes.c_ubyte), # regTemp (output)
    ctypes.POINTER(ctypes.c_uint)   # cbRegTemp (in/out)
]
zkfp.ZKFPM_DBMerge.restype = ctypes.c_int
# Declare ZKFPM_DBFree to release the algorithm operation instance
zkfp.ZKFPM_DBFree.argtypes = [ctypes.c_void_p]
zkfp.ZKFPM_DBFree.restype = ctypes.c_int

# ==== KHỞI TẠO SLK20R ====
print("🎯 Khởi tạo máy quét vân tay...")
assert zkfp.ZKFPM_Init() == 0, "Không thể khởi tạo SDK máy quét vân tay."
count = zkfp.ZKFPM_GetDeviceCount()
print("🔍 Số thiết bị kết nối:", count)
assert count > 0, "Không tìm thấy thiết bị quét vân tay nào."

handle = zkfp.ZKFPM_OpenDevice(0)
assert handle, "Không thể mở thiết bị quét"

params = TZKFPCapParams()
zkfp.ZKFPM_GetCaptureParams(handle, ctypes.byref(params))
img_width, img_height = params.imgWidth, params.imgHeight
print(f"📷 Kích thước ảnh: {img_width}x{img_height}, DPI: {params.nDPI}")

# ==== BỘ ĐỆM ====
image_buf = (ctypes.c_ubyte * (img_width * img_height))()
template_buf_size = 2048
template_bufs = [(ctypes.c_ubyte * template_buf_size)() for _ in range(3)]
template_lens = [ctypes.c_uint(template_buf_size) for _ in range(3)]

# ==== THU THẬP 3 LẦN VÂN TAY ====
collected_templates_raw = [] # Store raw bytes for merging
for i in range(3):
    print(f"\n👉 Lần {i+1}: Vui lòng đặt ngón tay lên máy quét...")
    for _ in range(30): # Tối đa 15 giây chờ mỗi lần quét
        ret = zkfp.ZKFPM_AcquireFingerprint(
            handle,
            image_buf,
            img_width * img_height,
            template_bufs[i],
            ctypes.byref(template_lens[i])
        )
        if ret == 0:
            print(f"✅ Lần {i+1}: Lấy vân tay thành công!")
            collected_templates_raw.append(template_bufs[i][:template_lens[i].value])
            break
        time.sleep(0.5)
    else:
        print(f"❌ Lần {i+1}: Không lấy được vân tay.")
        zkfp.ZKFPM_CloseDevice(handle)
        zkfp.ZKFPM_Terminate()
        exit(1)

zkfp.ZKFPM_CloseDevice(handle)
zkfp.ZKFPM_Terminate()

if len(collected_templates_raw) < 3:
    print("❌ Không đủ 3 mẫu vân tay để merge.")
    exit(1)

# ==== INITIALIZE DB CACHE FOR MERGING ====
hDBCache = zkfp.ZKFPM_DBInit() # Create the algorithm operation instance
assert hDBCache, "Không thể khởi tạo bộ đệm DB (DB Cache) để merge vân tay."
print("✅ Đã khởi tạo bộ đệm DB để merge vân tay.")

# ==== MERGE 3 TEMPLATE ====
print("\n🔄 Đang merge 3 mẫu vân tay...")
merged_template_buf = (ctypes.c_ubyte * template_buf_size)()
merged_template_len = ctypes.c_uint(template_buf_size)

# Ensure templates are correctly cast for the C function
# The C function expects POINTER(ctypes.c_ubyte), so we create c_ubyte arrays
# from the collected raw bytes.
t1_c = (ctypes.c_ubyte * len(collected_templates_raw[0]))(*collected_templates_raw[0])
t2_c = (ctypes.c_ubyte * len(collected_templates_raw[1]))(*collected_templates_raw[1])
t3_c = (ctypes.c_ubyte * len(collected_templates_raw[2]))(*collected_templates_raw[2])


ret_merge = zkfp.ZKFPM_DBMerge( # Use ZKFPM_DBMerge or ZKFPM_GenRegTemplate
    hDBCache,
    t1_c,
    t2_c,
    t3_c,
    merged_template_buf,
    ctypes.byref(merged_template_len)
)

if ret_merge == 0:
    print("✅ Merge vân tay thành công!")
    final_template_data = bytes(merged_template_buf[:merged_template_len.value])
else:
    print(f"❌ Lỗi khi merge vân tay. Mã lỗi: {ret_merge}")
    # You can refer to libzkfperrdef.h for error codes
    zkfp.ZKFPM_DBFree(hDBCache) # Release the DB Cache handle on error
    exit(1)

# ==== RELEASE DB CACHE AFTER MERGING ====
zkfp.ZKFPM_DBFree(hDBCache) # Release the algorithm operation instance
print("✅ Đã giải phóng bộ đệm DB.")


# ==== KẾT NỐI MÁY CHẤM CÔNG ====
print(f"\n🌐 Kết nối máy chấm công tại {DEVICE_IP}...")
zk = ZK(DEVICE_IP, port=4370, timeout=5, force_udp=True)
conn = None
try:
    conn = zk.connect()
    conn.disable_device()

    uid_int = int(USER_ID)

    # ==== KIỂM TRA & XÓA/TẠO MỚI USER ====
    print(f"Checking for user {USER_ID} on device...")
    users = conn.get_users()
    user_exists = False
    for u in users:
        if u.uid == uid_int:
            user_exists = True
            break

    if user_exists:
        print(f"🗑️ User {USER_ID} đã tồn tại. Đang xóa user cũ...")
        conn.delete_user(uid=uid_int)
        print(f"✅ Đã xóa user {USER_ID}.")
        time.sleep(0.5) # Give the device a moment
    else:
        print(f"👤 User {USER_ID} chưa tồn tại.")

    print(f"➕ Tạo mới user {USER_ID}...")
    conn.set_user(uid=uid_int, name=f"User {USER_ID}", privilege=const.USER_DEFAULT)
    # Re-fetch user details after creation
    users = conn.get_users()
    user = next((u for u in users if u.uid == uid_int), None)
    if not user:
        raise Exception(f"Không thể tạo hoặc tìm thấy user {USER_ID} sau khi tạo.")

    # ==== GỬI TEMPLATE ====
    print("📤 Gửi template vân tay đã merge lên máy chấm công...")

    # Create a list of 10 Finger objects, with the merged template for FINGER_ID
    # and empty templates for other finger IDs.
    templates_to_send = []
    for i in range(10):
        if i == FINGER_ID:
            finger_obj = Finger(uid=uid_int, fid=i, valid=True, template=final_template_data)
        else:
            # For other finger IDs, send a dummy finger with an empty template
            # This is important to ensure other fingers for the user are not inadvertently set
            finger_obj = Finger(uid=uid_int, fid=i, valid=False, template=b'')
        templates_to_send.append(finger_obj)

    conn.save_user_template(user, templates_to_send)

    conn.enable_device()
    print("✅ Đã đồng bộ vân tay thành công.")

except Exception as e:
    print(f"❌ Lỗi: {e}")
finally:
    if conn:
        conn.disconnect()
        print("Đã ngắt kết nối khỏi máy chấm công.")