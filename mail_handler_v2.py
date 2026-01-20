# mail_handler_v2.py
import imaplib
import email
import re
import time
from email.header import decode_header

# Cấu hình IMAP GMX
IMAP_SERVER = "imap.gmx.net"
IMAP_PORT = 993

def _decode_str(header_value):
    if not header_value: return ""
    try:
        decoded_list = decode_header(header_value)
        text = ""
        for content, encoding in decoded_list:
            if isinstance(content, bytes):
                text += content.decode(encoding or "utf-8", errors="ignore")
            else: text += str(content)
        return text
    except: return str(header_value)

def get_instagram_code_strict(gmx_user, gmx_pass, target_ig_username):
    """
    Login GMX -> Lấy Code từ mail Instagram MỚI NHẤT.
    Hỗ trợ cả mail 'Verify account' và 'Authentication/Security code'.
    """
    if not gmx_user or not gmx_pass:
        raise Exception("MISSING_GMX_CREDS")
    
    if "@" not in gmx_user: gmx_user += "@gmx.net"

    print(f"   [IMAP] Connecting to {gmx_user}...")
    mail = None
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(gmx_user, gmx_pass)
    except Exception as e:
        raise Exception(f"GMX_LOGIN_FAIL: {str(e)}")

    found_code = None
    
    try:
        # Quét 3 lần
        for attempt in range(3):
            print(f"   [IMAP] Scanning inbox (Attempt {attempt+1}/3)...")
            mail.select("INBOX")
            
            # Tìm tất cả mail từ Instagram (Mới nhất lên đầu)
            status, messages = mail.search(None, '(FROM "Instagram")')
            
            if status == "OK" and messages[0]:
                mail_ids = messages[0].split()
                mail_ids.sort(key=lambda x: int(x), reverse=True)
                
                # Quét 3 mail mới nhất
                recent_mails = mail_ids[:3] 
                
                for mid in recent_mails:
                    _, msg_data = mail.fetch(mid, "(RFC822)")
                    full_msg = email.message_from_bytes(msg_data[0][1])
                    
                    # --- CẬP NHẬT: MỞ RỘNG TỪ KHÓA SUBJECT ---
                    subject = _decode_str(full_msg["Subject"]).lower()
                    valid_keywords = [
                        "verify your account", "xác thực", 
                        "two-factor", "authentication", "xác thực 2 yếu tố",
                        "security code", "mã bảo mật", 
                        "login code", "mã đăng nhập"
                    ]
                    
                    # Nếu tiêu đề không chứa từ khóa nào liên quan -> Bỏ qua
                    if not any(k in subject for k in valid_keywords):
                        continue 
                    
                    # Check Body
                    body_content = ""
                    if full_msg.is_multipart():
                        for part in full_msg.walk():
                            if part.get_content_type() == "text/plain":
                                body_content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    else:
                        body_content = full_msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    
                    # Check Username (Chỉ check nếu là mail Verify Account, mail Auth đôi khi không có username)
                    if "verify" in subject and target_ig_username.lower() not in body_content.lower():
                        continue

                    # Extract 6-digit Code (hoặc 8 số nếu có)
                    # Ưu tiên tìm 6 số trước
                    m = re.search(r'\b(\d{6})\b', body_content)
                    if not m:
                        # Fallback: Tìm 8 số (Backup code)
                        m = re.search(r'\b(\d{8})\b', body_content)
                    
                    if m:
                        found_code = m.group(1)
                        print(f"   [IMAP] => FOUND CODE: {found_code} (Subject: {subject})")
                        return found_code
            
            if attempt < 2: 
                print("   [IMAP] No code found. Waiting 5s...")
                time.sleep(5)
            
    except Exception as e:
        if "GMX_LOGIN_FAIL" in str(e): raise e
        print(f"   [IMAP] Scan Error: {e}")
    finally:
        try: mail.logout()
        except: pass
        
    return None