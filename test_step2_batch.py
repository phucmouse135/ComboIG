# test_step2_batch.py
import os
import time
from config_utils import get_driver
from step1_login import InstagramLoginStep
from step2_exceptions import InstagramExceptionStep

INPUT_FILE = "input.txt"
JSON_COOKIE_PATH = "Wed New Instgram  2026 .json"

def parse_input_line(line):
    parts = line.strip().split("\t")
    if len(parts) < 7: return None
    
    # 0:UID, 1:MAIL LK, 2:USER, 3:PASS, 4:2FA, 5:PHÔI GỐC, 6:PASS MAIL
    return {
        "uid": parts[0].strip(),
        "linked_mail": parts[1].strip(), # Lấy thêm Mail LK
        "username": parts[2].strip(),
        "password": parts[3].strip(),
        "gmx_user": parts[5].strip(),
        "gmx_pass": parts[6].strip()
    }

def run_account_test(index, acc):
    user = acc['username']
    print(f"\n{'='*20} ACC {index}: {user} {'='*20}")
    
    driver = None
    try:
        driver = get_driver(headless=False) 
        
        # Step 1
        print(f"   [Flow] Starting Step 1...")
        step1 = InstagramLoginStep(driver)
        step1.load_base_cookies(JSON_COOKIE_PATH)
        status_s1 = step1.perform_login(acc['username'], acc['password'])
        print(f"   [Flow] Step 1 Result: {status_s1}")
        
        # Step 2
        print(f"   [Flow] Starting Step 2...")
        step2 = InstagramExceptionStep(driver)
        
        # TRUYỀN THÊM linked_mail VÀO ĐÂY
        final_status = step2.handle_status(
            status_s1, 
            acc['username'], 
            acc['gmx_user'], 
            acc['gmx_pass'],
            linked_mail=acc['linked_mail'] # Param mới
        )
        
        print(f"   [✅ RESULT] {user} -> PASSED: {final_status}")

    except Exception as e:
        print(f"   [❌ RESULT] {user} -> FAILED")
        print(f"   [Reason] {str(e)}")
        
    finally:
        if driver:
            print(f"   [👁 VISUAL CHECK] Waiting 5s...")
            time.sleep(5)
            try: driver.quit()
            except: pass

def main():
    if not os.path.exists(INPUT_FILE): return
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    accounts = []
    for line in lines:
        if line.strip():
            parsed = parse_input_line(line)
            if parsed: accounts.append(parsed)

    print(f"\n>>> LOADED {len(accounts)} ACCOUNTS <<<\n")
    for i, acc in enumerate(accounts, 1):
        run_account_test(i, acc)
        if i < len(accounts): time.sleep(3)

if __name__ == "__main__":
    main()