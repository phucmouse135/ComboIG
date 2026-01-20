# test_step1_batch.py
import os
import time
from config_utils import get_driver
from step1_login import InstagramLoginStep

# --- CẤU HÌNH ---
INPUT_FILE = "input.txt"
JSON_COOKIE_PATH = "Wed New Instgram  2026 .json"

def parse_input_line(line):
    parts = line.strip().split("\t")
    # Cấu trúc: 0:UID, 1:MailLK, 2:User, 3:PassIG ...
    if len(parts) < 4: return None
    return {
        "username": parts[2].strip(),
        "password": parts[3].strip()
    }

def process_account(index, acc_data):
    username = acc_data["username"]
    password = acc_data["password"]
    
    print(f"\n{'='*20} ACC {index}: {username} {'='*20}")
    
    driver = None
    try:
        # 1. Init Driver (Mỗi acc 1 driver mới để sạch session)
        driver = get_driver(headless=False) 
        
        # 2. Init Step 1
        step1 = InstagramLoginStep(driver)
        
        # 3. Load Cookie
        step1.load_base_cookies(JSON_COOKIE_PATH)
        
        # 4. Login
        status = step1.perform_login(username, password)
        
        print(f"   [RESULT] {username} => STATUS: {status}")
        # input("Nhấn Enter để kết thúc...")
        
        
    except Exception as e:
        print(f"   [ERROR] {username}: {str(e)}")
    finally:
        if driver:
            driver.quit()
            print(f"   [INFO] Closed driver for {username}")

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"File {INPUT_FILE} not found!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Lọc dòng trống
    valid_lines = [l for l in lines if l.strip()]
    print(f">>> Found {len(valid_lines)} accounts in input.txt")

    for i, line in enumerate(valid_lines, 1):
        acc = parse_input_line(line)
        if acc:
            process_account(i, acc)
        else:
            print(f"Skipping invalid line {i}: {line[:20]}...")

    print("\n>>> BATCH TEST STEP 1 COMPLETED <<<")

if __name__ == "__main__":
    main()