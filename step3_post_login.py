# step3_post_login.py
import time
from selenium.webdriver.common.by import By
from config_utils import wait_element, wait_and_click, wait_dom_ready

class InstagramPostLoginStep:
    def __init__(self, driver):
        self.driver = driver

    def process_post_login(self, username):
        """
        Luồng chính xử lý sau khi Login thành công:
        1. Xử lý các màn hình chắn (Cookie, Terms, Lỗi Page, Popup...).
        2. Điều hướng vào Profile.
        3. Crawl Dữ liệu (Post, Follower, Following).
        4. Trích xuất Cookie mới.
        """
        print(f"   [Step 3] Processing Post-Login for {username}...")
        
        # 1. Xử lý các Popup/Màn hình chắn (Vòng lặp check)
        self._handle_interruptions()
        
        # 2. Điều hướng vào Profile
        self._navigate_to_profile(username)
        
        # 3. Crawl Dữ liệu
        data = self._crawl_data(username)
        
        # 4. Lấy Cookie mới
        data['cookie'] = self._get_cookie_string()
        
        return data

    def _handle_interruptions(self):
        """Xử lý vòng lặp các màn hình chắn với cơ chế Click mạnh mẽ (XPath + JS)."""
        max_checks = 10 
        
        for i in range(max_checks):
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                
                # --- A. PAGE BROKEN ---
                if "page isn’t working" in body_text or "contact the site owner" in body_text:
                    print("   [Step 3] Detected 'Page Broken'. Redirecting to Home...")
                    self.driver.get("https://www.instagram.com/")
                    wait_dom_ready(self.driver, timeout=10)
                    time.sleep(3)
                    continue

                # --- B. COOKIE CONSENT (Đã tối ưu) ---
                if "allow the use of cookies" in body_text:
                    print("   [Step 3] Handling 'Allow Cookies'...")
                    
                    # 1. Thử Click bằng Selenium (XPath mạnh)
                    cookie_xpaths = [
                        "//button[contains(., 'Allow all cookies')]", 
                        "//div[@role='button'][contains(., 'Allow all cookies')]",
                        "//*[contains(text(), 'Allow all cookies')]",
                        "//button[contains(., 'Cho phép tất cả')]",
                        "//*[contains(text(), 'Cho phép tất cả')]"
                    ]
                    clicked = False
                    for xpath in cookie_xpaths:
                        if wait_and_click(self.driver, By.XPATH, xpath, timeout=2):
                            clicked = True; break
                    
                    # 2. Fallback: JS Click (Nếu Selenium trượt)
                    if not clicked:
                        print("   [Step 3] Cookie XPath failed. Using JS Injection...")
                        self.driver.execute_script("""
                            var keywords = ['allow all cookies', 'cho phép tất cả'];
                            var els = document.querySelectorAll('button, div[role="button"], span');
                            for (var e of els) {
                                if (keywords.some(k => e.innerText.toLowerCase().includes(k))) { e.click(); break; }
                            }
                        """)
                    
                    time.sleep(3)
                    continue

                # --- C. REVIEW AND AGREE (TERMS) - (CẬP NHẬT MẠNH MẼ) ---
                if "review and agree" in body_text or "agree to terms" in body_text or "xem xét và đồng ý" in body_text:
                    print("   [Step 3] Handling 'Review Terms'...")
                    
                    # --- BƯỚC 1: CLICK NEXT (TIẾP) ---
                    # XPath quét rộng hơn (contains dấu chấm)
                    next_xpaths = [
                        "//button[contains(., 'Next')]", 
                        "//div[@role='button'][contains(., 'Next')]",
                        "//button[contains(., 'Tiếp')]",
                        "//div[@role='button'][contains(., 'Tiếp')]"
                    ]
                    
                    next_btn = None
                    for xpath in next_xpaths:
                        next_btn = wait_element(self.driver, By.XPATH, xpath, timeout=2)
                        if next_btn: break
                    
                    if next_btn:
                        try:
                            # Scroll xuống để tránh bị che
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_btn)
                            time.sleep(1)
                            next_btn.click()
                        except:
                            # JS Click dự phòng cho nút Next
                            self.driver.execute_script("arguments[0].click();", next_btn)
                        print("   [Step 3] Clicked Next (Terms).")
                        time.sleep(3) # Chờ load đoạn Agree
                    
                    # --- BƯỚC 2: CLICK AGREE (ĐỒNG Ý) ---
                    agree_xpaths = [
                        "//button[contains(., 'Agree to terms')]",
                        "//div[@role='button'][contains(., 'Agree to terms')]",
                        "//*[contains(text(), 'I Agree')]",
                        "//button[contains(., 'Đồng ý')]",
                        "//div[@role='button'][contains(., 'Đồng ý')]"
                    ]
                    
                    agree_clicked = False
                    for xpath in agree_xpaths:
                        agree_btn = wait_element(self.driver, By.XPATH, xpath, timeout=3)
                        if agree_btn:
                            try:
                                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", agree_btn)
                                time.sleep(1)
                                agree_btn.click()
                                agree_clicked = True
                            except:
                                self.driver.execute_script("arguments[0].click();", agree_btn)
                                agree_clicked = True
                            break
                    
                    # Fallback JS cho nút Agree nếu XPath không tìm thấy
                    if not agree_clicked:
                        print("   [Step 3] Agree XPath failed. Using JS Injection...")
                        self.driver.execute_script("""
                            var keywords = ['agree', 'đồng ý', 'chấp nhận'];
                            var els = document.querySelectorAll('button, div[role="button"], span');
                            for (var e of els) {
                                if (keywords.some(k => e.innerText.toLowerCase().includes(k))) { e.click(); break; }
                            }
                        """)

                    wait_dom_ready(self.driver, timeout=5)
                    time.sleep(2)
                    continue

                # --- D. POPUP THÔNG BÁO (Messaging / Notif) - (CẬP NHẬT MẠNH MẼ) ---
                if "messaging tab has a new look" in body_text or "turn on notifications" in body_text or "bật thông báo" in body_text:
                    print("   [Step 3] Handling Notification Popup...")
                    
                    # Danh sách các nút từ chối/ok phổ biến
                    popup_xpaths = [
                        "//button[contains(., 'Not Now')]", 
                        "//div[@role='button'][contains(., 'Not Now')]",
                        "//button[contains(., 'Lúc khác')]",
                        "//button[contains(., 'Không phải bây giờ')]",
                        "//button[contains(., 'Cancel')]",
                        "//button[contains(., 'OK')]"
                    ]
                    
                    popup_clicked = False
                    for xpath in popup_xpaths:
                        if wait_and_click(self.driver, By.XPATH, xpath, timeout=2):
                            popup_clicked = True
                            break
                    
                    # JS Fallback cho Popup
                    if not popup_clicked:
                        print("   [Step 3] Popup XPath failed. Using JS Injection...")
                        self.driver.execute_script("""
                            var keywords = ['not now', 'lúc khác', 'cancel', 'hủy', 'ok'];
                            var els = document.querySelectorAll('button, div[role="button"], span');
                            for (var e of els) {
                                if (keywords.some(k => e.innerText.toLowerCase() === k)) { e.click(); break; }
                            }
                        """)
                    
                    time.sleep(1)
                    continue

                # --- E. CHECK SUCCESS ---
                # Kiểm tra Nav Bar (Home Icon, Explore Icon...)
                if len(self.driver.find_elements(By.CSS_SELECTOR, "svg[aria-label='Home'], svg[aria-label='Trang chủ'], svg[aria-label='Explore']")) > 0:
                    print("   [Step 3] Detected Home Screen. Interruptions cleared.")
                    break
                
                # Fallback check link
                if len(self.driver.find_elements(By.CSS_SELECTOR, "a[href*='explore']")) > 0:
                     break

                time.sleep(1)
            except Exception as e:
                pass

    def _navigate_to_profile(self, username):
        """Click vào biểu tượng Profile để vào trang cá nhân."""
        print("   [Step 3] Navigating to Profile...")
        
        profile_selectors = [
            f"a[href='/{username}/']",          # Link trực tiếp
            "img[alt$='profile picture']",      # Ảnh Avatar nhỏ
            "svg[aria-label='Profile']",        # Icon Profile
            "svg[aria-label='Trang cá nhân']"
        ]
        
        clicked = False
        for sel in profile_selectors:
            el = wait_element(self.driver, By.CSS_SELECTOR, sel, timeout=3)
            if el:
                try: 
                    el.click()
                    clicked = True
                    break
                except: pass
        
        # Nếu click thất bại, truy cập thẳng URL
        if not clicked:
            print("   [Step 3] Click failed. Forcing URL navigation...")
            self.driver.get(f"https://www.instagram.com/{username}/")
        
        wait_dom_ready(self.driver)
        # Chờ Username xuất hiện (Confirm đã vào đúng trang)
        wait_element(self.driver, By.XPATH, f"//*[contains(text(), '{username}')]", timeout=5)

    def _crawl_data(self, username):
        """Crawl dữ liệu Posts, Followers, Following."""
        print(f"   [Step 3] Crawling data for {username}...")
        data = {"posts": "0", "followers": "0", "following": "0"}

        try:
            # 1. Posts (Tìm text chứa 'posts' -> lấy thẻ span con)
            posts_el = wait_element(self.driver, By.XPATH, "//*[contains(text(), 'posts')]/span | //*[contains(text(), 'bài viết')]/span", timeout=3)
            if posts_el: 
                data["posts"] = posts_el.text.replace(",", "").replace(".", "")

            # 2. Followers (Lấy từ thẻ A href='followers')
            followers_el = wait_element(self.driver, By.XPATH, f"//a[contains(@href, 'followers')]//span", timeout=3)
            if followers_el:
                # Ưu tiên lấy attribute title vì nó chứa số đầy đủ
                val = followers_el.get_attribute("title")
                if not val: val = followers_el.text
                data["followers"] = val.replace(",", "").replace(".", "")

            # 3. Following (Lấy từ thẻ A href='following')
            following_el = wait_element(self.driver, By.XPATH, f"//a[contains(@href, 'following')]//span", timeout=3)
            if following_el: 
                data["following"] = following_el.text.replace(",", "").replace(".", "")
            
            print(f"   [Step 3] Extracted: Posts={data['posts']} | Followers={data['followers']} | Following={data['following']}")
            
        except Exception as e:
            print(f"   [Step 3] Crawl Warning: {e}")

        return data

    def _get_cookie_string(self):
        """Lấy toàn bộ cookie hiện tại và gộp thành chuỗi."""
        try:
            cookies = self.driver.get_cookies()
            return "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        except:
            return ""