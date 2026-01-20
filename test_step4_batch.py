# test_full_batch.py
import os
import time
from config_utils import get_driver
from step1_login import InstagramLoginStep
from step2_exceptions import InstagramExceptionStep
from step3_post_login import InstagramPostLoginStep
from step4_2fa import Instagram2FAStep

INPUT_FILE = "input.txt"
OUTPUT_FILE = "output_full_2fa.txt"
JSON_COOKIE_PATH = "Wed New Instgram  2026 .json"

def parse_input_line(line):
    parts = line.strip().split("\t")
    if len(parts) < 7: return None
    return {
        "raw_parts": parts,
        "uid": parts[0],
        "linked_mail": parts[1],
        "username": parts[2],
        "password": parts[3],
        "gmx_user": parts[5],
        "gmx_pass": parts[6]
    }

def run_full_process():
    if not os.path.exists(INPUT_FILE): return
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    results = [] 
    
    for i, line in enumerate(lines):
        if not line.strip(): 
            results.append(line)
            continue
            
        acc = parse_input_line(line)
        if not acc:
            results.append(line)
            continue

        print(f"\n{'='*20} PROCESSING ACC {acc['username']} {'='*20}")
        driver = None
        updated_parts = acc['raw_parts']
        while len(updated_parts) < 12: updated_parts.append("")

        try:
            driver = get_driver(headless=False)
            
            # --- STEP 1: LOGIN ---
            step1 = InstagramLoginStep(driver)
            step1.load_base_cookies(JSON_COOKIE_PATH)
            status = step1.perform_login(acc['username'], acc['password'])
            print(f"   [Step 1] Status: {status}")

            # --- STEP 2: HANDLE EXCEPTIONS ---
            step2 = InstagramExceptionStep(driver)
            step2.handle_status(status, acc['username'], acc['gmx_user'], acc['gmx_pass'], acc['linked_mail'])
            print(f"   [Step 2] Passed.")

            # --- STEP 3: CRAWL & COOKIE ---
            step3 = InstagramPostLoginStep(driver)
            data = step3.process_post_login(acc['username'])
            
            # Update Data (Posts, Followers, Following, Cookie)
            updated_parts[8] = data['posts']
            updated_parts[9] = data['followers']
            updated_parts[10] = data['following']
            updated_parts[11] = data['cookie']
            print(f"   [Step 3] Data Crawled.")

            # --- STEP 4: ENABLE 2FA ---
            # Chỉ chạy nếu chưa có 2FA hoặc muốn update
            step4 = Instagram2FAStep(driver)
            secret_key = step4.setup_2fa(acc['gmx_user'], acc['gmx_pass'], acc['linked_mail'])
            
            # Update Secret Key vào cột 2FA (Index 4)
            updated_parts[4] = secret_key
            print(f"   [Step 4] 2FA Enabled! Key: {secret_key}")
            
            print(f"   [✅ SUCCESS] Full flow completed for {acc['username']}")

        except Exception as e:
            print(f"   [❌ FAIL] {acc['username']} Error: {e}")
            # Nếu muốn, có thể ghi lỗi vào cột nào đó
        
        finally:
            if driver: driver.quit()
        
        # Save Result
        results.append("\t".join(updated_parts) + "\n")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
            out.writelines(results)

    print(f"\nDONE. Check {OUTPUT_FILE}")

if __name__ == "__main__":
    run_full_process()