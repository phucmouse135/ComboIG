# test_full_batch.py
import os
import time
from config_utils import get_driver
from step1_login import InstagramLoginStep
from step2_exceptions import InstagramExceptionStep
from step3_post_login import InstagramPostLoginStep

INPUT_FILE = "input.txt"
OUTPUT_FILE = "output_updated.txt"
JSON_COOKIE_PATH = "Wed New Instgram  2026 .json"

def parse_input_line(line):
    parts = line.strip().split("\t")
    if len(parts) < 7: return None
    # Lưu lại toàn bộ parts để sau này update
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
    
    results = [] # Lưu danh sách dòng để ghi file
    
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
        
        # Mặc định dữ liệu update (giữ nguyên nếu fail)
        updated_parts = acc['raw_parts']
        # Đảm bảo list có đủ chỗ cho các cột Post(8), Followers(9), Following(10), Cookie(11)
        # (Index tính từ 0: 0..7 là pass mail, 8 là Post...)
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
            # Nếu Step 1 success thì Step 2 sẽ return luôn
            # Nếu Checkpoint thì giải, nếu Fail thì Raise Exception
            final_status = step2.handle_status(
                status, acc['username'], acc['gmx_user'], acc['gmx_pass'], acc['linked_mail']
            )
            print(f"   [Step 2] Result: {final_status}")

            # --- STEP 3: CRAWL & COOKIE ---
            # Chỉ chạy Step 3 nếu login thành công hoặc giải CP xong
            step3 = InstagramPostLoginStep(driver)
            data = step3.process_post_login(acc['username'])
            
            # Update Data vào List
            # Mapping cột theo yêu cầu:
            # 8: Post, 9: Followers, 10: Following, 11: Cookie
            updated_parts[8] = data['posts']
            updated_parts[9] = data['followers']
            updated_parts[10] = data['following']
            updated_parts[11] = data['cookie']
            
            print(f"   [✅ SUCCESS] Data updated for {acc['username']}")

        except Exception as e:
            print(f"   [❌ FAIL] {acc['username']} Stopped: {e}")
            # Nếu lỗi, có thể ghi chú vào cột nào đó hoặc giữ nguyên
        
        finally:
            if driver:
                driver.quit()
        
        # Ghép lại dòng text
        results.append("\t".join(updated_parts) + "\n")
        
        # Save real-time (an toàn hơn)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
            out.writelines(results)

    print(f"\nDONE. Check {OUTPUT_FILE}")

if __name__ == "__main__":
    run_full_process()