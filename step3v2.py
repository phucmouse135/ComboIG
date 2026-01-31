# step3_post_login.py
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config_utils import wait_element, wait_and_click, wait_dom_ready
import os

class InstagramPostLoginStep:
    def __init__(self, driver):
        self.driver = driver

    def _robust_click_button(self, selectors, timeout=20, retries=3):
        """Robust button clicking with multiple selectors and retries."""
        print(f"   [Step 3] Attempting to click button with {len(selectors)} selectors...")
        for attempt in range(retries):
            for selector_type, sel in selectors:
                try:
                    if selector_type == "css":
                        element = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                    elif selector_type == "xpath":
                        element = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((By.XPATH, sel)))
                    elif selector_type == "js":
                        result = self.driver.execute_script(sel)
                        if result:
                            result.click()
                            print(f"   [Step 3] Clicked via JS selector")
                            return True
                    else:
                        continue
                    element.click()
                    print(f"   [Step 3] Clicked {selector_type}: {sel}")
                    time.sleep(1)
                    return True
                except Exception as e:
                    print(f"   [Step 3] Failed to click {selector_type}: {sel} - {e}")
            time.sleep(1)
        print(f"   [Step 3] Failed to click button after {retries} attempts")
        return False

    def _safe_execute_script(self, script, default=None, retries=2):
        """Execute JS script with retry on timeout errors."""
        for attempt in range(retries + 1):
            try:
                return self.driver.execute_script(script)
            except Exception as e:
                if attempt < retries:
                    print(f"   [Step 3] JS execution failed (attempt {attempt+1}), retrying: {e}")
                    time.sleep(0.5)
                else:
                    print(f"   [Step 3] JS execution failed after {retries+1} attempts: {e}")
                    return default
        return default

    def process_post_login(self, username):
        """
        Luồng chính xử lý sau khi Login thành công:
        1. Xử lý các màn hình chắn (Cookie, Terms, Lỗi Page, Popup...).
        2. Điều hướng vào Profile.
        3. Crawl Dữ liệu (Post, Follower, Following).
        4. Trích xuất Cookie mới.
        """
        print(f"   [Step 3] Processing Post-Login for {username}...")
        
        # 1. Handle interruptions (popup check loop)
        self._handle_interruptions()
        
        # 1.5. Ensure back to home before navigating to profile
        print(f"   [Step 3] All popups handled. Ensuring back to home...")
        self.driver.get("https://www.instagram.com/")
        wait_dom_ready(self.driver, timeout=10)
        time.sleep(2)
        
        print(f"   [Step 3] Navigating to profile: {username}")
        profile_url = f"https://www.instagram.com/{username}/"
        self.driver.get(profile_url)
        wait_dom_ready(self.driver, timeout=10)
        time.sleep(2)  # Short wait for page load
        self._handle_interruptions()
        # 2. Điều hướng vào Profile (kiểm tra và retry nếu cần)
        max_navigate_attempts = 3
        for attempt in range(max_navigate_attempts):
            if self._navigate_to_profile(username):
                break
            if attempt < max_navigate_attempts - 1:
                print(f"   [Step 3] Navigate failed, redirecting to profile URL and retrying...")
                self.driver.get(profile_url)
                wait_dom_ready(self.driver, timeout=10)
                time.sleep(2)
        else:
            raise Exception("Failed to navigate to profile after retries")
        
        self._handle_interruptions() 
        # 3. Crawl Dữ liệu
        data = self._crawl_data(username)
        
        # 4. Lấy Cookie mới
        data['cookie'] = self._get_cookie_string()
        
        return data

    def _handle_interruptions(self):
        """
        Chiến thuật 'Aggressive Scan' (Tối ưu hóa bằng JS):
        Gộp kiểm tra Popup và kiểm tra Home vào 1 lần gọi JS để tăng tốc độ.
        """
        print("   [Step 3] Starting Aggressive Popup Scan...")
        
        # Check URL for cookie choice
        current_url = self.driver.current_url.lower()
        if "user_cookie_choice" in current_url:
            print("   [Step 3] Detected user_cookie_choice in URL, handling cookie popup...")
            cookie_button_selectors = [
                'button._a9--._ap36._asz1[tabindex="0"]',
                'button[class*="_a9--"][class*="_ap36"][class*="_asz1"]',
                'button[data-testid*="accept"]',
                'button[aria-label*="Accept cookies"]',
                'button[class*="cookie"]',
                'button[aria-label*="Accept"]',
                'button[title*="Accept"]',
                'button[data-action*="accept"]'
            ]
            
            for sel in cookie_button_selectors:
                try:
                    if sel in ['button[data-testid*="accept"]', 'button[aria-label*="Accept cookies"]', 'button[class*="cookie"]', 'button[aria-label*="Accept"]', 'button[title*="Accept"]', 'button[data-action*="accept"]']:
                        # For selectors that might match multiple, check text
                        cookie_btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for btn in cookie_btns:
                            if btn.is_displayed() and "allow all cookies" in btn.text.lower():
                                btn.click()
                                print("   [Step 3] Clicked 'Allow all cookies' button")
                                time.sleep(2)
                                return
                    else:
                        # For specific selectors
                        cookie_btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for btn in cookie_btns:
                            if btn.is_displayed():
                                btn.click()
                                print("   [Step 3] Clicked 'Allow all cookies' button")
                                time.sleep(2)
                                return
                except Exception as e:
                    print(f"   [Step 3] Failed to click cookie button with selector {sel}: {e}")
                    continue
            return
        
        # Check URL for unblock terms
        if "unblock" in current_url:
            print("   [Step 3] Detected unblock in URL, handling unblock terms...")
            # Click accept, agree, continue, next, done buttons
            buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, div[role='button']")
            for btn in buttons:
                if btn.is_displayed():
                    text = btn.text.lower().strip()
                    if any(word in text for word in ['accept', 'agree', 'continue', 'next', 'done']):
                        try:
                            btn.click()
                            print(f"   [Step 3] Clicked '{text}' button for unblock")
                            time.sleep(2)
                            return  # Exit after handling
                        except Exception as e:
                            print(f"   [Step 3] Failed to click {text} button: {e}")
            return
        
        end_time = time.time() + 120  # Quét trong 120 giây 
        popup_handling_attempts = 0
        max_popup_attempts = 10  # Prevent infinite loops
        
        while time.time() < end_time and popup_handling_attempts < max_popup_attempts: 
            try:
                # ---------------------------------------------------------
                # 1. QUÉT TRẠNG THÁI (POPUP + HOME) BẰNG JS
                # ---------------------------------------------------------
                action_result = self.driver.execute_script("""
                    // 1. KIỂM TRA HOME TRƯỚC (Điều kiện thoát nhanh)
                    // Nếu thấy icon Home và không có dialog nào che -> Báo về Home ngay
                    var homeIcon = document.querySelector("svg[aria-label='Home']") || document.querySelector("svg[aria-label='Trang chủ']");
                    var dialogs = document.querySelectorAll("div[role='dialog']");
                    var hasVisibleDialog = Array.from(dialogs).some(d => d.offsetParent !== null);
                    
                    if (homeIcon && !hasVisibleDialog) {
                        return 'HOME_SCREEN_CLEAR';
                    }

                    // 2. TỪ KHÓA POPUP
                    const keywords = {
                        'get_started': ['get started', 'bắt đầu'],
                        'agree_confirm': ['agree', 'đồng ý', 'update', 'cập nhật', 'confirm', 'xác nhận'],
                        'next_step': ['next', 'tiếp'],
                        'use_data_opt': ['use data across accounts', 'sử dụng dữ liệu trên các tài khoản'],
                        'cookie': ['allow all cookies', 'cho phép tất cả'],
                        'popup': ['not now', 'lúc khác', 'cancel', 'ok', 'hủy'], 
                        'age_check': ['18 or older', '18 tuổi trở lên', 'trên 18 tuổi'],
                        'account_center_check': ['choose an option', 'accounts center', 'use data across accounts'] 
                    };
                    const bodyText = document.body.innerText.toLowerCase();

                    // --- ƯU TIÊN: POPUP "ACCOUNTS CENTER" ---
                    if (keywords.account_center_check.some(k => bodyText.includes(k))) {
                        let buttons = document.querySelectorAll('button, div[role="button"], span');
                        for (let btn of buttons) {
                            let t = btn.innerText.toLowerCase().trim();
                            if (t === 'next' || t === 'tiếp' || t === 'continue') {
                                btn.click();
                                if (btn.tagName === 'SPAN' && btn.parentElement) btn.parentElement.click();
                                return 'ACCOUNTS_CENTER_NEXT';
                            }
                        }
                    }
                    
                    // --- XỬ LÝ CHECKPOINT TUỔI (RADIO BUTTON) ---
                    let radio18 = document.querySelector('input[type="radio"][value="above_18"]');
                    if (radio18) {
                        radio18.click();
                        let container = radio18.closest('div[role="button"]');
                        if (container) container.click();
                        let visualCircle = radio18.previousElementSibling;
                        if (visualCircle) visualCircle.click();

                        // Auto click Agree sau 1s
                        setTimeout(() => {
                            let btns = document.querySelectorAll('button, div[role="button"]');
                            for(let b of btns) {
                                if(b.innerText.toLowerCase().includes('agree') || b.innerText.toLowerCase().includes('đồng ý')) { b.click(); }
                            }
                        }, 500); 
                        return 'AGE_CHECK_CLICKED';
                    }
                    
                    // Fallback tuổi theo text
                    let ageLabels = document.querySelectorAll("span, label");
                    for(let el of ageLabels) {
                        if (el.innerText.includes("18 or older") || el.innerText.includes("18 tuổi trở lên")) {
                             let parentBtn = el.closest('div[role="button"]');
                             if (parentBtn) { parentBtn.click(); return 'AGE_CHECK_CLICKED'; }
                        }
                    }

                    // A. TÌM VÀ CHỌN OPTION (Use Data)
                    const labels = document.querySelectorAll('div, span, label');
                    for (let el of labels) {
                        if (el.offsetParent === null) continue;
                        let txt = el.innerText.toLowerCase().trim();
                        if (keywords.use_data_opt.some(k => txt === k)) {
                            el.scrollIntoView({behavior: "instant", block: "center"});
                            el.click(); return 'OPTION_SELECTED';
                        }
                    }

                    // B. TÌM VÀ CLICK NÚT BẤM CHUNG
                    const elements = document.querySelectorAll('button, div[role="button"]');
                    
                    // Enhanced cookie button selectors for better reliability (similar to step 1)
                    let cookieSelectors = [
                        'button._a9--._ap36._asz1[tabindex="0"]',
                        'button[class*="_a9--"][class*="_ap36"][class*="_asz1"]'
                    ];
                    
                    for (let sel of cookieSelectors) {
                        let cookieBtns = document.querySelectorAll(sel);
                        for (let btn of cookieBtns) {
                            if (btn.offsetParent !== null && btn.innerText.toLowerCase().includes('allow all cookies')) {
                                btn.click();
                                return 'COOKIE_CLICKED';
                            }
                        }
                    }
                    
                    // Fallback: check all buttons for cookie text
                    let allButtons = document.querySelectorAll('button');
                    for (let btn of allButtons) {
                        if (btn.offsetParent !== null && btn.innerText.toLowerCase().includes('allow all cookies')) {
                            btn.click();
                            return 'COOKIE_CLICKED';
                        }
                    }
                    
                    for (let el of elements) {
                        if (el.offsetParent === null) continue; 
                        let txt = el.innerText.toLowerCase().trim();
                        if (!txt) continue;

                        if (keywords.get_started.some(k => txt === k)) {
                            el.scrollIntoView({behavior: "instant", block: "center"});
                            el.click(); return 'GET_STARTED_CLICKED';
                        }
                        if (keywords.agree_confirm.some(k => txt.includes(k))) {
                            el.scrollIntoView({behavior: "instant", block: "center"});
                            el.click(); return 'AGREE_CLICKED';
                        }
                        if (keywords.next_step.some(k => txt === k)) {
                            el.scrollIntoView({behavior: "instant", block: "center"});
                            el.click(); return 'NEXT_CLICKED';
                        }
                        if (keywords.cookie.some(k => txt.includes(k))) {
                            el.click(); return 'COOKIE_CLICKED';
                        }
                        if (keywords.popup.some(k => txt === k)) {
                            el.click(); return 'POPUP_CLICKED';
                        }
                    }
                    return null;
                """)

                if action_result == 'HOME_SCREEN_CLEAR':
                    print("   [Step 3] Home Screen detected. Verifying no remaining popups...")
                    # Double-check that we're actually ready to proceed
                    time.sleep(1.5)  # Reduced from 2 for faster verification
                    try:
                        # Check again for any remaining dialogs or overlays
                        final_check = self.driver.execute_script("""
                            var dialogs = document.querySelectorAll('div[role="dialog"], div[role="alertdialog"], div[aria-modal="true"]');
                            var hasVisibleDialog = Array.from(dialogs).some(d => d.offsetParent !== null && d.getAttribute('aria-hidden') !== 'true');
                            
                            // Check for overlays that might block interaction
                            var overlays = document.querySelectorAll('div[aria-hidden="false"], div[data-testid*="modal"], div[style*="z-index"]');
                            var hasVisibleOverlay = Array.from(overlays).some(o => {
                                var style = window.getComputedStyle(o);
                                return style.display !== 'none' && style.visibility !== 'hidden' && o.offsetParent !== null;
                            });
                            
                            // Check for unusual login popups specifically
                            var unusualLogin = document.body.innerText.toLowerCase().includes('we detected an unusual login attempt') ||
                                              document.body.innerText.toLowerCase().includes('continue') ||
                                              document.body.innerText.toLowerCase().includes('this was me');
                            
                            return !(hasVisibleDialog || hasVisibleOverlay || unusualLogin);
                        """)
                        
                        if final_check:
                            print("   [Step 3] Home Screen Clear confirmed. Done.")
                            break  # [EXIT LOOP] Đã thành công
                        else:
                            print("   [Step 3] Still have popups/overlays/unusual login elements, continuing...")
                            # Try to handle any remaining unusual login popups
                            self._handle_remaining_popups()
                            popup_handling_attempts += 1
                            continue
                    except Exception as e:
                        print(f"   [Step 3] Error in final verification: {e}")
                        popup_handling_attempts += 1
                        continue

                if action_result:
                    print(f"   [Step 3] Action triggered: {action_result}")
                    
                    if action_result == 'AGREE_CLICKED':
                        time.sleep(2); self._check_crash_recovery()  # Reduced from 3
                    elif action_result == 'OPTION_SELECTED':
                        print("   [Step 3] Option selected. Waiting for Next button...")
                        time.sleep(0.5)  # Reduced from 1
                    elif action_result == 'AGE_CHECK_CLICKED': 
                        print("   [Step 3] Handled Age Verification (18+). Waiting...")
                        time.sleep(2)  # Reduced from 3
                    else:
                        time.sleep(1.0)  # Reduced from 1.5
                    continue

                # ---------------------------------------------------------
                # 2. CHECK CRASH (Python side fallback)
                # ---------------------------------------------------------
                try:
                    curr_url = self.driver.current_url.lower()
                    if "ig_sso_users" in curr_url or "/api/v1/" in curr_url or "error" in curr_url:
                        print(f"   [Step 3] Crash URL detected. Reloading Home...")
                        self.driver.get("https://www.instagram.com/")
                        time.sleep(4); continue

                    body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    if "page isn’t working" in body_text or "http error" in body_text:
                        print("   [Step 3] Crash Text detected. Reloading Home...")
                        self.driver.get("https://www.instagram.com/")
                        time.sleep(4); continue
                except: pass

                # --------------------------------------------------------- 
                # Additional popup handling for specific cases (similar to step 2)
                # ---------------------------------------------------------
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    
                    # CONFIRM_TRUSTED_DEVICE
                    if "confirm trusted device" in body_text or "xác nhận thiết bị đáng tin cậy" in body_text:
                        print("   [Step 3] Handling Confirm Trusted Device...")
                        success = self._robust_click_button([
                            ("js", """
                                var buttons = document.querySelectorAll('button, [role=\"button\"], div[role=\"button\"]');
                                for (var i = 0; i < buttons.length; i++) {
                                    var text = buttons[i].textContent.trim().toLowerCase();
                                    if (text.includes('close') || text.includes('x') || text.includes('cancel') ||
                                        text.includes('not now') || text.includes('skip') || text.includes('dismiss')) {
                                        return buttons[i];
                                    }
                                }
                                return null;
                            """),
                            ("css", "div.x1i10hfl.xjqpnuy.xc5r6h4.xqeqjp1.x1phubyo.x972fbf.x10w94by.x1qhh985.x14e42zd.xdl72j9.x2lah0s.x3ct3a4.xdj266r.x14z9mp.xat24cr.x1lziwak.x2lwn1j.xeuugli.xexx8yu.x18d9i69.x1hl2dhg.xggy1nq.x1ja2u2z.x1t137rt.x1q0g3np.x1lku1pv.x1a2a7pz.x6s0dn4.xjyslct.x1obq294.x5a5i1n.xde0f50.x15x8krk.x1ejq31n.x18oe1m7.x1sy0etr.xstzfhl.x9f619.x1ypdohk.x1f6kntn.xwhw2v2.x10w6t97.xl56j7k.x17ydfre.xf7dkkf.xv54qhq.x1n2onr6.x2b8uid.xlyipyv.x87ps6o.x5c86q.x18br7mf.x1i0vuye.xh8yej3.x1aavi5t.x1h6iz8e.xixcex4.xk4oym4.xl3ioum.x3nfvp2"),
                            ("css", "div[role='button'][tabindex='0']"),
                            ("css", "div[role='button']"),
                            ("xpath", "//button[contains(text(), 'Close')]"),
                            ("xpath", "//button[contains(text(), 'Cancel')]"),
                            ("xpath", "//button[contains(text(), 'Not now')]"),
                        ])
                        if success:
                            print("   [Step 3] Successfully handled Confirm Trusted Device")
                            time.sleep(2)
                            continue
                    
                    # SUBSCRIBE_OR_CONTINUE
                    if "subscribe or continue" in body_text or "đăng ký hoặc tiếp tục" in body_text:
                        print("   [Step 3] Handling Subscribe Or Continue...")
                        self._robust_click_button([("xpath", "(//input[@type='radio'])[2]"), ("css", "input[type='radio']:nth-of-type(2)")])
                        time.sleep(1)
                        self._robust_click_button([
                            ("xpath", "//button[contains(text(), 'Continue') or contains(text(), 'Tiếp tục')]"),
                            ("css", "button[type='submit']"),
                        ])
                        time.sleep(2)
                        continue
                    
                    # REVIEW_AGREE_DATA_CHANGES
                    if "review and agree" in body_text or "xem xét và đồng ý" in body_text:
                        print("   [Step 3] Handling Review and Agree Data Changes...")
                        success = self._robust_click_button([
                            ("xpath", "//div[@role='button' and contains(text(), 'Next')]"),
                            ("css", "div[role='button'][tabindex='0']"),
                        ])
                        if success:
                            print("   [Step 3] Successfully clicked Next on data changes popup")
                            time.sleep(2)
                            continue
                    
                    # COOKIE_CONSENT_POPUP (additional fallback)
                    if "allow all cookies" in body_text or "cho phép tất cả cookie" in body_text:
                        print("   [Step 3] Handling Cookie Consent Popup (fallback)...")
                        success = self._robust_click_button([
                            ("css", "button._a9--._ap36._asz1[tabindex='0']"),
                            ("xpath", "//button[contains(text(), 'Allow all cookies')]"),
                            ("css", "div.x1uugd1q[role='button'][tabindex='0']"),
                        ], timeout=10, retries=2)
                        if success:
                            print("   [Step 3] Successfully clicked Allow all cookies (fallback)")
                            time.sleep(2)
                            continue
                    
                except Exception as e:
                    print(f"   [Step 3] Error in additional popup handling: {e}")

                time.sleep(0.3)  # Reduced from 0.5 for faster scanning

                # Check for fail statuses
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    fail_keywords = {
                        "LOGIN_FAILED_INCORRECT": ["login failed incorrect", "incorrect password", "wrong password", "invalid credentials"],
                        "SUSPENDED": ["account suspended", "tài khoản bị đình chỉ", "your account has been suspended"],
                        "ACCOUNT_DISABLED": ["account disabled", "tài khoản bị vô hiệu hóa"],
                        "UNUSUAL_LOGIN": ["unusual login", "đăng nhập bất thường"],
                        "TRY_ANOTHER_DEVICE": ["try another device", "thử thiết bị khác"],
                        "2FA_REQUIRED": ["two-factor authentication required", "yêu cầu xác thực hai yếu tố"],
                        "GET_HELP_LOG_IN": ["get help logging in", "cần giúp đỡ đăng nhập"],
                        "LOG_IN_ANOTHER_DEVICE": ["log in another device", "đăng nhập thiết bị khác"],
                        "CONFIRM_YOUR_IDENTITY": ["confirm your identity", "xác nhận danh tính"],
                        "PAGE_BROKEN": ["page not found", "trang không tìm thấy"],
                        "SUSPENDED_PHONE": ["phone suspended", "điện thoại bị đình chỉ"],
                        "DISABLE_ACCOUNT": ["disable account", "vô hiệu hóa tài khoản"]
                    }
                    for status, keywords in fail_keywords.items():
                        if any(keyword in body_text for keyword in keywords):
                            raise Exception(f"STOP_FLOW_EXCEPTION: {status}")
                except Exception as e:
                    if "STOP_FLOW_EXCEPTION" in str(e):
                        raise e
                    # ignore other errors

            except Exception as e:
                popup_handling_attempts += 1
                time.sleep(1)
        
        # Check if we exceeded max popup handling attempts
        if popup_handling_attempts >= max_popup_attempts:
            print(f"   [Step 3] Exceeded max popup handling attempts ({max_popup_attempts}). Proceeding anyway.")
            return  # Exit the method to continue with navigation

    def _check_crash_recovery(self):
        """Hàm phụ trợ check crash nhanh sau khi click Agree."""
        try:
            wait_dom_ready(self.driver, timeout=5)
        except: pass

    def _handle_remaining_popups(self):
        """Handle any remaining unusual login or other popups that Step 2 might have missed."""
        print("   [Step 3] Attempting to handle remaining popups...")
        try:
            # Try to click Continue or This Was Me buttons
            continue_buttons = self.driver.execute_script("""
                var buttons = document.querySelectorAll('button, div[role="button"]');
                var found = [];
                for (var btn of buttons) {
                    var text = btn.textContent.toLowerCase().trim();
                    if (text.includes('continue') || text.includes('tiếp tục') || 
                        text.includes('this was me') || text.includes('đây là tôi')) {
                        found.push(btn);
                    }
                }
                return found.slice(0, 3); // Return up to 3 buttons
            """)
            
            for btn in continue_buttons:
                try:
                    btn.click()
                    print("   [Step 3] Clicked remaining popup button")
                    time.sleep(3)
                    return True
                except:
                    continue
                    
            # Try ESC key as fallback
            self.driver.execute_script("""
                var event = new KeyboardEvent('keydown', {key: 'Escape'});
                document.dispatchEvent(event);
            """)
            print("   [Step 3] Sent ESC key to close popup")
            time.sleep(2)
            
        except Exception as e:
            print(f"   [Step 3] Error handling remaining popups: {e}")
        
        return False

    def _ensure_instagram_ready(self):
        """Đảm bảo đã vào Instagram và sẵn sàng để navigate."""
        print("   [Step 3] Ensuring Instagram is ready...")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                current_url = self.driver.current_url
                print(f"   [Step 3] Current URL: {current_url}")
                
                # Check if we're on Instagram domain
                if "instagram.com" not in current_url:
                    print("   [Step 3] Not on Instagram domain, navigating to home...")
                    self.driver.get("https://www.instagram.com/")
                    wait_dom_ready(self.driver, timeout=10)
                    time.sleep(3)
                    continue
                
                # Check for basic Instagram elements
                body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                
                # If we see login form, something went wrong
                if "log in" in body_text or "username" in body_text or "password" in body_text:
                    print("   [Step 3] Detected login form, something went wrong. Refreshing...")
                    self.driver.refresh()
                    wait_dom_ready(self.driver, timeout=10)
                    time.sleep(3)
                    continue
                
                # Check for common Instagram elements
                instagram_indicators = [
                    "home", "search", "explore", "reels", "messages", 
                    "notifications", "create", "profile", "posts", "followers"
                ]
                
                found_indicators = sum(1 for indicator in instagram_indicators if indicator in body_text)
                
                if found_indicators >= 3:
                    print(f"   [Step 3] Instagram ready (found {found_indicators} indicators)")
                    return True
                else:
                    print(f"   [Step 3] Instagram not ready yet (found {found_indicators} indicators), waiting...")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"   [Step 3] Error checking Instagram readiness: {e}")
                time.sleep(2)
        
        print("   [Step 3] Warning: Could not confirm Instagram readiness, proceeding anyway")
        return False

    def _navigate_to_profile(self, username):
        """Truy cập thẳng URL profile để đảm bảo vào đúng trang."""
        print(f"   [Step 3] Navigating to Profile: {username}...")
        
        # Luôn truy cập thẳng URL để tránh lỗi click icon
        profile_url = f"https://www.instagram.com/{username}/"
        self.driver.get(profile_url)
        
        wait_dom_ready(self.driver, timeout=15)
        time.sleep(3)  # Wait for dynamic content
        
        # Chờ Username xuất hiện (Confirm đã vào đúng trang), retry nếu cần
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                current_url = self.driver.current_url
                print(f"   [Step 3] Attempt {attempt+1}/{max_attempts} - Current URL: {current_url}")
                
                # Check if we're on the correct profile URL
                if username.lower() not in current_url.lower():
                    print(f"   [Step 3] URL mismatch, expected username '{username}' in URL")
                    self.driver.get(profile_url)
                    wait_dom_ready(self.driver, timeout=10)
                    time.sleep(2)
                    continue
                
                # Check for profile-specific elements
                profile_indicators = [
                    f"@{username}", username, "posts", "followers", "following"
                ]
                
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                
                # Check if profile loaded
                username_found = any(indicator in body_text for indicator in profile_indicators)
                
                if username_found:
                    print(f"   [Step 3] Profile page confirmed for {username}")
                    
                    # Additional check: look for profile picture or bio area
                    try:
                        profile_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                            "img[alt*='" + username + "'], div[data-testid='user-biography'], header section")
                        if profile_elements:
                            print("   [Step 3] Profile elements found, navigation successful")
                            return True
                    except:
                        pass
                    
                    return True
                
                # Check for error pages
                if "sorry, this page isn't available" in body_text.lower():
                    print(f"   [Step 3] Profile not found or private: {username}")
                    return False
                
                if "this account is private" in body_text.lower():
                    print(f"   [Step 3] Private account: {username}")
                    return False
                
                print(f"   [Step 3] Profile not loaded yet, attempt {attempt+1}/{max_attempts}")
                time.sleep(2)
                
            except Exception as e:
                print(f"   [Step 3] Error checking profile: {e}")
                time.sleep(2)
        
        print(f"   [Step 3] Warning: Could not confirm profile page for {username}, proceeding anyway")
        return False

    def _crawl_data(self, username):
        print(f"   [Step 3] Crawling data for {username}...")
        
        # Verify we're on the correct profile page before crawling
        current_url = self.driver.current_url
        if username.lower() not in current_url.lower():
            print(f"   [Step 3] ERROR: Not on profile page for {username}. Current URL: {current_url}")
            return {"posts": "0", "followers": "0", "following": "0"}
        
        final_data = {"posts": "0", "followers": "0", "following": "0"}
        
        # Scroll down to load stats
        self.driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        
        js_crawl = """
            function getInfo() {
                let res = {posts: "0", followers: "0", following: "0", source: "none"};
                
                // 1. DÙNG MỎ NEO LINK FOLLOWERS (Tương thích cả UL/LI và DIV)
                let folLink = document.querySelector("a[href*='followers']");
                
                if (folLink) {
                    // CÁCH A: Cấu trúc DIV
                    let wrapper = folLink.closest('div'); 
                    if (wrapper && wrapper.parentElement) {
                        let container = wrapper.parentElement;
                        let divs = Array.from(container.children).filter(el => el.tagName === 'DIV');
                        if (divs.length >= 3) {
                            res.posts = divs[0].innerText;
                            res.followers = divs[1].innerText;
                            res.following = divs[2].innerText;
                            res.source = "div_structure";
                            return res;
                        }
                    }
                    // CÁCH B: Cấu trúc UL/LI
                    let ulContainer = folLink.closest("ul");
                    if (ulContainer) {
                        let items = ulContainer.querySelectorAll("li");
                        if (items.length >= 3) {
                            res.posts = items[0].innerText;
                            res.followers = items[1].innerText;
                            res.following = items[2].innerText;
                            res.source = "ul_structure";
                            return res;
                        }
                    }
                }

                // 2. FALLBACK: META TAG
                try {
                    let meta = document.querySelector('meta[property="og:description"]') || document.querySelector('meta[name="description"]');
                    if (meta) {
                        res.raw_meta = meta.getAttribute('content');
                        res.source = "meta";
                        return res;
                    }
                } catch(e) {}

                return res;
            }
            return getInfo();
        """

        # Hàm làm sạch số (100 posts -> 100)
        def clean_num(val):
            if not val: return "0"
            val = str(val).replace("\n", " ").strip()
            m = re.search(r'([\d.,]+[kKmM]?)', val)
            return m.group(1) if m else "0"

        def parse_meta(text):
            if not text: return "0", "0", "0"
            text = text.lower().replace(",", "").replace(".", ".")
            p = re.search(r'(\d+[km]?)\s+(posts|bài viết|beiträge)', text)
            f1 = re.search(r'(\d+[km]?)\s+(followers|người theo dõi)', text)
            f2 = re.search(r'(\d+[km]?)\s+(following|đang theo dõi)', text)
            if not p: p = re.search(r'(posts|bài viết)\s+(\d+[km]?)', text)
            return (p.group(1) if p else "0"), (f1.group(1) if f1 else "0"), (f2.group(1) if f2 else "0")

        for i in range(1, 4):
            try:
                time.sleep(1.5)
                raw_js = self.driver.execute_script(js_crawl)
                
                p, f1, f2 = "0", "0", "0"
                
                # Ưu tiên nguồn cấu trúc (DIV hoặc UL)
                if raw_js and raw_js.get("source") in ["div_structure", "ul_structure"]:
                    p = clean_num(raw_js.get("posts"))
                    f1 = clean_num(raw_js.get("followers"))
                    f2 = clean_num(raw_js.get("following"))
                    print(f"   [Step 3] Crawled via DOM ({raw_js.get('source')}): P={p}, F1={f1}, F2={f2}")

                # Nguồn Meta Tag
                elif raw_js and raw_js.get("source") == "meta":
                    p, f1, f2 = parse_meta(raw_js.get("raw_meta"))
                    print(f"   [Step 3] Crawled via META: P={p}, F1={f1}, F2={f2}")

                temp_data = {"posts": p, "followers": f1, "following": f2}

                # Always accept the data (retry handled in gui_app.py)
                final_data = temp_data
                print(f"   [Step 3] Success (Attempt {i}): {final_data}")
                break

            except Exception as e:
                print(f"   [Step 3] Crawl Error (Attempt {i}): {e}")

        return final_data

    def _get_cookie_string(self):
        """Lấy toàn bộ cookie hiện tại và gộp thành chuỗi, với chuẩn hóa."""
        try:
            cookies = self.driver.get_cookies()
            # Chuẩn hóa: loại bỏ khoảng trắng và encode value
            import urllib.parse
            cookie_parts = []
            for c in cookies:
                name = c['name']
                value = urllib.parse.quote(c['value'].strip())
                cookie_parts.append(f"{name}={value}")
            return "; ".join(cookie_parts)
        except:
            return ""

    def _check_status(self):
        # Copy of _check_verification_result from step2
        # Timeout protection for verification result (max 60s)
        # Optimized with JS checks to avoid hangs and speed up detection
        TIMEOUT = 20
        end_time = time.time() + TIMEOUT
        consecutive_failures = 0
        max_consecutive_failures = 20  # If JS fails 20 times in a row, consider timeout
        try:
            WebDriverWait(self.driver, 10).until(lambda d: self._safe_execute_script("return document.readyState") == "complete")
        except Exception as e:
            print(f"   [Step 3] Page not ready after 10s: {e}")
        while time.time() < end_time:
            try:
                # Check URL for unblock terms
                current_url = self.driver.current_url.lower()
                if "unblock" in current_url:
                    return "UNBLOCK_TERMS"
                
                # Check URL for cookie choice
                if "user_cookie_choice" in current_url:
                    return "COOKIE_CONSENT_POPUP"
                
                
                #  Check your email or This email will replace all existing contact and login info on your account
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('check your email') || document.body.innerText.toLowerCase().includes('this email will replace all existing contact and login info on your account')"):
                    return "CHECKPOINT_MAIL"
                
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('change password') || document.body.innerText.toLowerCase().includes('new password') || document.body.innerText.toLowerCase().includes('create a strong password') || document.body.innerText.toLowerCase().includes('change your password to secure your account')"):
                    # nếu có new confirm new password thì require change password
                    if len(self._safe_execute_script("return Array.from(document.querySelectorAll('input[type=\"password\"]'));", [])) >= 2:
                        return "REQUIRE_PASSWORD_CHANGE"
                    else:
                        return "CHANGE_PASSWORD"
                
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('add phone number') || document.body.innerText.toLowerCase().includes('send confirmation') || document.body.innerText.toLowerCase().includes('log into another account')"):
                    return "SUSPENDED_PHONE"
                
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('select your birthday') || document.body.innerText.toLowerCase().includes('add your birthday')"):
                    return "BIRTHDAY_SCREEN"
                
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('allow the use of cookies') || document.body.innerText.toLowerCase().includes('posts') || document.body.innerText.toLowerCase().includes('save your login info')"):
                    return "SUCCESS"
                
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('suspended') || document.body.innerText.toLowerCase().includes('đình chỉ')"):
                    return "SUSPENDED"
                # some thing wrong 
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('something went wrong') || document.body.innerText.toLowerCase().includes('đã xảy ra sự cố')"):
                    return "SOMETHING_WRONG"
                
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('sorry, there was a problem') || document.body.innerText.toLowerCase().includes('please try again')"):
                    return "RETRY_UNUSUAL_LOGIN"
                
                # Check for wrong code
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('code isn\\'t right') || document.body.innerText.toLowerCase().includes('mã không đúng') || document.body.innerText.toLowerCase().includes('incorrect') || document.body.innerText.toLowerCase().includes('wrong code') || document.body.innerText.toLowerCase().includes('invalid') || document.body.innerText.toLowerCase().includes('the code you entered')"):
                    return "WRONG_CODE"
                
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('create a password at least 6 characters long') || document.body.innerText.toLowerCase().includes('password must be at least 6 characters')"):
                    return "REQUIRE_PASSWORD_CHANGE"
                
                # enter your real birthday
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('enter your real birthday') || document.body.innerText.toLowerCase().includes('nhập ngày sinh thật của bạn')"):
                    return "REAL_BIRTHDAY_REQUIRED"
                
                # use another profile va log into instagram => dang nhap lai voi data moi 
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('log into instagram') || document.body.innerText.toLowerCase().includes('use another profile')"):
                    return "RETRY_UNUSUAL_LOGIN"  
                
                # URL checks
                # current_url = self.driver.current_url
                # if "instagram.com/" in current_url and "challenge" not in current_url:
                #     return "SUCCESS"
                
                # Element-based checks for logged in state - BE MORE CAUTIOUS
                # Check for home screen indicators but also verify no blocking popups
                home_indicators = self._safe_execute_script("return document.body.innerText.toLowerCase().includes('posts') || document.body.innerText.toLowerCase().includes('followers') || document.body.innerText.toLowerCase().includes('search') || document.body.innerText.toLowerCase().includes('home')")
                
                if home_indicators:
                    # Additional check: ensure no modal dialogs are blocking the interface
                    has_blocking_popups = self._safe_execute_script("""
                        var dialogs = document.querySelectorAll('div[role="dialog"], div[role="alertdialog"]');
                        var hasVisibleDialog = Array.from(dialogs).some(d => d.offsetParent !== null);
                        
                        // Also check for overlays that might block interaction
                        var overlays = document.querySelectorAll('div[aria-hidden="false"], div[data-testid*="modal"], div[style*="z-index"]');
                        var hasVisibleOverlay = Array.from(overlays).some(o => {
                            var style = window.getComputedStyle(o);
                            return style.display !== 'none' && style.visibility !== 'hidden' && o.offsetParent !== null;
                        });
                        
                        return hasVisibleDialog || hasVisibleOverlay;
                    """)
                    
                    if not has_blocking_popups:
                        return "LOGGED_IN_SUCCESS"
                    else:
                        print("   [Step 3] Home screen detected but blocking popups/overlays present")
                
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('save your login info') || document.body.innerText.toLowerCase().includes('we can save your login info') || document.body.innerText.toLowerCase().includes('lưu thông tin đăng nhập')"):
                    return "LOGGED_IN_SUCCESS"
                
                # save info or not now
                if self._safe_execute_script("return (document.querySelector('button[type=\"submit\"]') !== null && (document.body.innerText.toLowerCase().includes('save info') || document.body.innerText.toLowerCase().includes('not now') || document.body.innerText.toLowerCase().includes('để sau')))"):
                    return "LOGGED_IN_SUCCESS"
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('save your login info') || document.body.innerText.toLowerCase().includes('we can save your login info') || document.body.innerText.toLowerCase().includes('lưu thông tin đăng nhập')"):
                    return "LOGGED_IN_SUCCESS"
                
                # save info or not now
                if self._safe_execute_script("return (document.querySelector('button[type=\"submit\"]') !== null && (document.body.innerText.toLowerCase().includes('save info') || document.body.innerText.toLowerCase().includes('not now') || document.body.innerText.toLowerCase().includes('để sau')))"):
                    return "LOGGED_IN_SUCCESS"
                
                
                
                # Want to subscribe or continue
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('subscribe')"):
                    return "SUBSCRIBE_OR_CONTINUE"
                
                # Check if "get new code" option is available
                if self._safe_execute_script("return document.body.innerText.toLowerCase().includes('get a new one') || document.body.innerText.toLowerCase().includes('get new code') || document.body.innerText.toLowerCase().includes('get a new code') || document.body.innerText.toLowerCase().includes('didn\\'t get a code') || document.body.innerText.toLowerCase().includes('didn\\'t receive') || document.body.innerText.toLowerCase().includes('resend') || document.body.innerText.toLowerCase().includes('send new code') || document.body.innerText.toLowerCase().includes('request new code')"):
                    return "CAN_GET_NEW_CODE"
                
                consecutive_failures = 0  # Reset on successful check
            except Exception as e:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    print(f"   [Step 3] Too many JS failures in verification check: {e}")
                    break
            time.sleep(1.0)
        # Log current state for debugging timeout
        try:
            current_url = self.driver.current_url
            body_text = self.driver.find_element(By.TAG_NAME, "body").text[:500]  # First 500 chars
            print(f"   [Step 3] TIMEOUT reached. Current URL: {current_url}")
            print(f"   [Step 3] Page body preview: {body_text}...")
            
            # Capture screenshot for timeout (unknown status)
            timestamp = int(time.time())
            screenshot_dir = "screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f"timeout_unknown_status_{timestamp}.png")
            self.driver.save_screenshot(screenshot_path)
            print(f"   [Step 3] Screenshot saved for timeout unknown status: {screenshot_path}")
            
            # Additional check: If we're on checkpoint mail screen but regex didn't catch it
            # Check for radio buttons (typical in checkpoint mail)
            try:
                radios = self._safe_execute_script("return Array.from(document.querySelectorAll('input[type=\"radio\"]')).length;", 0)
                if radios > 0:
                    print(f"   [Step 3] Found {radios} radio buttons, likely checkpoint mail screen")
                    return "CHECKPOINT_MAIL"
            except:
                pass
            
            # Check for code input fields
            try:
                code_inputs = self._safe_execute_script("return Array.from(document.querySelectorAll('input[type=\"text\"], input[name=\"security_code\"], input[id=\"security_code\"])).length;", 0)
                if code_inputs > 0:
                    print(f"   [Step 3] Found {code_inputs} text inputs, likely checkpoint mail screen")
                    return "CHECKPOINT_MAIL"
            except:
                pass
            
            # Check for common checkpoint mail keywords that might have been missed
            try:
                full_body = self._safe_execute_script("return document.body.innerText.toLowerCase();", "")
                checkpoint_keywords = ["checkpoint", "verify", "verification", "security code", "confirmation code", "email verification", "mã xác nhận", "xác nhận email"]
                if any(keyword in full_body for keyword in checkpoint_keywords):
                    print("   [Step 3] Found checkpoint-related keywords, likely checkpoint mail screen")
                    return "CHECKPOINT_MAIL"
            except:
                pass
                
        except Exception as e:
            print(f"   [Step 3] Error logging timeout state: {e}")
        return "TIMEOUT"