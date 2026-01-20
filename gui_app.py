import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import time
import csv
import os

# --- IMPORT CÁC LOGIC AUTOMATION ---
from config_utils import get_driver
from step1_login import InstagramLoginStep
from step2_exceptions import InstagramExceptionStep
from step3_post_login import InstagramPostLoginStep
from step4_2fa import Instagram2FAStep
# -----------------------------------

class AutomationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Automation Tool Pro")
        self.root.geometry("1280x720")
        
        # Variables
        self.file_path_var = tk.StringVar()
        self.thread_count_var = tk.IntVar(value=1)
        self.headless_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")
        
        # Stats
        self.total_count = 0
        self.processed_count = 0
        self.success_count = 0
        self.fail_count = 0
        
        # Control Flags
        self.is_running = False
        self.stop_event = threading.Event()
        self.msg_queue = queue.Queue()

        # --- CẤU HÌNH CỘT (ĐÃ SỬA LẠI CHO ĐÚNG INPUT) ---
        # Input mẫu: UID[0] | MAIL_LK[1] | USER[2] | PASS[3] | 2FA[4] | GMX_MAIL[5] | GMX_PASS[6] | RECOVERY[7] ...
        self.columns = (
            "uid",          # 0
            "mail_lk",      # 1 (Đã gộp chuẩn)
            "user",         # 2
            "pass",         # 3
            "2fa",          # 4
            "origin_mail",  # 5 (Phôi gốc)
            "pass_mail",    # 6
            "recovery",     # 7
            "post",         # 8
            "followers",    # 9
            "following",    # 10
            "cookie",       # 11
            "note"          # 12
        )
        
        self.setup_ui()
        self.process_queue()

    def setup_ui(self):
        # --- STYLE ---
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", rowheight=25)
        style.map('Treeview', background=[('selected', '#3498db')])

        # --- TOP FRAME: CONFIG & INPUT ---
        top_frame = ttk.LabelFrame(self.root, text="Configuration & Input", padding=10)
        top_frame.pack(fill="x", padx=10, pady=5)

        # File Selection
        ttk.Label(top_frame, text="Input File (.txt):").grid(row=0, column=0, sticky="w")
        ttk.Entry(top_frame, textvariable=self.file_path_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(top_frame, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=5)
        ttk.Button(top_frame, text="Reload Data", command=self.reload_data).grid(row=0, column=3, padx=5)
        
        # Manual Input
        ttk.Button(top_frame, text="Manual Input", command=self.open_manual_input).grid(row=0, column=4, padx=5)

        # Run Config
        ttk.Label(top_frame, text="Threads:").grid(row=1, column=0, sticky="w", pady=10)
        tk.Spinbox(top_frame, from_=1, to=50, textvariable=self.thread_count_var, width=5).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Checkbutton(top_frame, text="Run Headless (Hidden)", variable=self.headless_var).grid(row=1, column=1, sticky="e", padx=5)

        # Control Buttons
        self.btn_start = ttk.Button(top_frame, text="START", command=self.start_automation, width=15)
        self.btn_start.grid(row=1, column=3, padx=5)
        
        self.btn_stop = ttk.Button(top_frame, text="STOP", command=self.stop_automation, state="disabled", width=15)
        self.btn_stop.grid(row=1, column=4, padx=5)

        # --- STATS FRAME ---
        stats_frame = ttk.Frame(self.root)
        stats_frame.pack(fill="x", padx=10, pady=0)
        
        self.lbl_progress = ttk.Label(stats_frame, text="Progress: 0/0", font=("Arial", 10, "bold"))
        self.lbl_progress.pack(side="left", padx=10)
        
        self.lbl_success = ttk.Label(stats_frame, text="Success: 0", foreground="green", font=("Arial", 10, "bold"))
        self.lbl_success.pack(side="left", padx=10)

        self.lbl_status = ttk.Label(stats_frame, textvariable=self.status_var, foreground="blue")
        self.lbl_status.pack(side="right", padx=10)

        # --- MAIN TABLE FRAME ---
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical")
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal")

        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", 
                                 yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set, selectmode="extended")
        
        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)
        
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        # --- CẤU HÌNH HEADERS & WIDTH (ĐÃ CHỈNH LẠI) ---
        headers = {
            "uid": "UID",
            "mail_lk": "MAIL LK",      # Gộp chuẩn
            "user": "USER",
            "pass": "PASS",
            "2fa": "2FA",
            "origin_mail": "GMX MAIL",
            "pass_mail": "GMX PASS",
            "recovery": "RECOVERY",
            "post": "POST",
            "followers": "FOLLOWERS",
            "following": "FOLLOWING",
            "cookie": "COOKIE",
            "note": "NOTE"
        }
        
        col_width = {
            "uid": 80, "mail_lk": 180, "user": 100, "pass": 80, 
            "2fa": 150, "origin_mail": 180, "pass_mail": 80, "recovery": 150, 
            "post": 50, "followers": 70, "following": 70, "cookie": 100, "note": 100
        }

        for col in self.columns:
            self.tree.heading(col, text=headers.get(col, col))
            self.tree.column(col, width=col_width.get(col, 100), minwidth=50)

        # Tags
        self.tree.tag_configure("success", background="#d4edda") 
        self.tree.tag_configure("error", background="#f8d7da")   
        self.tree.tag_configure("running", background="#fff3cd") 

        # Context Menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Copy Cell Value", command=self.copy_cell_value)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete Selected Rows", command=self.delete_selected_rows)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # --- BOTTOM FRAME: ACTIONS ---
        bottom_frame = ttk.LabelFrame(self.root, text="Data Operations", padding=10)
        bottom_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(bottom_frame, text="Delete Selected", command=self.delete_selected_rows).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Clear All", command=self.clear_all_data).pack(side="left", padx=5)
        ttk.Separator(bottom_frame, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(bottom_frame, text="Export Success", command=lambda: self.export_data("success")).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Export Failed", command=lambda: self.export_data("failed")).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Export No Success", command=lambda: self.export_data("no_success")).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Export All", command=lambda: self.export_data("all")).pack(side="left", padx=5)

    # --- SỬA LỖI UI MANUAL INPUT (BUTTON LUÔN HIỂN THỊ) ---
    def open_manual_input(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Manual Input (Tab Separated)")
        dialog.geometry("800x600") # Kích thước mặc định lớn hơn
        dialog.minsize(600, 400)
        
        # 1. Button Frame (Pack BOTTOM -> Luôn ở đáy)
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        # 2. Text Frame (Pack TOP + Expand -> Chiếm phần còn lại)
        txt_frame = ttk.Frame(dialog)
        txt_frame.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 0))
        
        scroll_y = ttk.Scrollbar(txt_frame)
        scroll_y.pack(side="right", fill="y")
        
        txt_input = tk.Text(txt_frame, wrap="none", yscrollcommand=scroll_y.set)
        txt_input.pack(side="left", fill="both", expand=True)
        scroll_y.config(command=txt_input.yview)
        
        def submit():
            raw_data = txt_input.get("1.0", "end").strip()
            if raw_data:
                lines = raw_data.split("\n")
                added_count = 0
                for line in lines:
                    if line.strip():
                        parts = line.strip().split("\t")
                        # Fill thiếu cột
                        while len(parts) < len(self.columns): parts.append("")
                        # Reset trạng thái
                        parts[-1] = "Pending"
                        self.tree.insert("", "end", values=parts)
                        added_count += 1
                self.update_stats()
                messagebox.showinfo("Success", f"Added {added_count} accounts.")
                dialog.destroy()

        # Nút bấm nằm trong btn_frame (đáy)
        ttk.Button(btn_frame, text="Submit Data", command=submit).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Clear", command=lambda: txt_input.delete("1.0", "end")).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)
        
        ttk.Label(btn_frame, text="Paste data from Excel/Text (Tab separated)", font=("Arial", 9, "italic")).pack(side="left")

    # --- HANDLERS KHÁC ---
    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if filename:
            self.file_path_var.set(filename)
            self.load_data_from_file(filename)

    def reload_data(self):
        path = self.file_path_var.get()
        if path and os.path.exists(path):
            self.load_data_from_file(path)
        else:
            messagebox.showwarning("Warning", "File path is invalid or empty.")

    def load_data_from_file(self, filepath):
        self.clear_all_data(confirm=False)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split("\t")
                        while len(parts) < len(self.columns): parts.append("")
                        parts[-1] = "Pending"
                        self.tree.insert("", "end", values=parts)
            self.update_stats()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load file: {e}")

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if item:
            self.tree.selection_set(item)
            self.selected_cell_col = col 
            self.context_menu.post(event.x_root, event.y_root)

    def copy_cell_value(self):
        try:
            selected_item = self.tree.selection()[0]
            col_idx = int(self.selected_cell_col.replace("#", "")) - 1
            value = self.tree.item(selected_item)['values'][col_idx]
            self.root.clipboard_clear()
            self.root.clipboard_append(str(value))
        except: pass

    def delete_selected_rows(self):
        selected = self.tree.selection()
        if not selected: return
        if messagebox.askyesno("Confirm", f"Delete {len(selected)} rows?"):
            for item in selected: self.tree.delete(item)
            self.update_stats()

    def clear_all_data(self, confirm=True):
        if confirm and not messagebox.askyesno("Confirm", "Clear ALL data?"): return
        for item in self.tree.get_children(): self.tree.delete(item)
        self.update_stats()

    def update_stats(self):
        items = self.tree.get_children()
        self.total_count = len(items)
        self.lbl_progress.config(text=f"Progress: {self.processed_count}/{self.total_count}")
        
    def start_automation(self):
        items = self.tree.get_children()
        pending_items = [i for i in items if self.tree.item(i)['values'][-1] == "Pending"]
        
        if not pending_items:
            messagebox.showinfo("Info", "No 'Pending' items to process.")
            return

        self.is_running = True
        self.stop_event.clear()
        
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal", text="STOP")
        self.status_var.set("Running...")
        
        self.processed_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.lbl_success.config(text="Success: 0")
        
        num_threads = self.thread_count_var.get()
        threading.Thread(target=self.thread_manager, args=(pending_items, num_threads), daemon=True).start()

    def stop_automation(self):
        if messagebox.askyesno("Confirm", "Stop automation process?"):
            self.is_running = False
            self.stop_event.set()
            self.btn_stop.config(text="Stopping...", state="disabled")
            self.status_var.set("Stopping...")

    def thread_manager(self, items, num_threads):
        task_queue = queue.Queue()
        for item in items: task_queue.put(item)

        def worker():
            while not self.stop_event.is_set():
                try:
                    item_id = task_queue.get(timeout=1)
                except queue.Empty: break
                
                self.process_single_account(item_id)
                task_queue.task_done()
                if not self.is_running: break

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)

        for t in threads: t.join()
        self.msg_queue.put(("ALL_DONE", None))

    # --- HÀM XỬ LÝ AUTOMATION (MAPPING ĐÃ SỬA) ---
    def process_single_account(self, item_id):
        values = list(self.tree.item(item_id)['values'])
        
        # MAPPING CỘT MỚI (Khớp với danh sách self.columns bên trên)
        # 0:UID, 1:MAIL_LK, 2:USER, 3:PASS, 4:2FA, 5:GMX_MAIL, 6:GMX_PASS ...
        acc = {
            "uid": values[0], 
            "linked_mail": values[1], # MAIL LK
            "username": values[2],    # USER
            "password": values[3],    # PASS
            "gmx_user": values[5],    # PHÔI GỐC (index 5)
            "gmx_pass": values[6]     # PASS MAIL (index 6)
        }
        
        self.msg_queue.put(("UPDATE_STATUS", (item_id, "Running...", "running")))
        driver = None
        
        try:
            # 1. Setup Driver
            headless = self.headless_var.get()
            driver = get_driver(headless=headless) 

            # 2. Step 1: Login
            step1 = InstagramLoginStep(driver)
            step1.load_base_cookies("Wed New Instgram  2026 .json") 
            status_s1 = step1.perform_login(acc['username'], acc['password'])
            
            if "FAIL" in status_s1:
                self.msg_queue.put(("FAIL_CRITICAL", (item_id, status_s1)))
                return

            # 3. Step 2: Handle Exception
            step2 = InstagramExceptionStep(driver)
            step2.handle_status(status_s1, acc['username'], acc['gmx_user'], acc['gmx_pass'], acc['linked_mail'])

            # 4. Step 3: Crawl (Realtime Update)
            step3 = InstagramPostLoginStep(driver)
            crawled_data = step3.process_post_login(acc['username'])
            
            # Cập nhật các cột Post(8), Follow(9), Following(10)
            self.msg_queue.put(("UPDATE_CRAWL", (item_id, {
                "post": crawled_data.get('posts', '0'),
                "followers": crawled_data.get('followers', '0'),
                "following": crawled_data.get('following', '0')
            })))

            # 5. Step 4: 2FA
            step4 = Instagram2FAStep(driver)
            secret_key = step4.setup_2fa(acc['gmx_user'], acc['gmx_pass'], acc['linked_mail'])
            
            # Update 2FA(4) và Note
            self.msg_queue.put(("SUCCESS", (item_id, secret_key)))

        except Exception as e:
            error_msg = str(e)
            if "STOP_FLOW" in error_msg: error_msg = error_msg.replace("STOP_FLOW_", "")
            self.msg_queue.put(("FAIL_CRITICAL", (item_id, error_msg)))
        finally:
            if driver: 
                try: driver.quit()
                except: pass

    def process_queue(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "UPDATE_STATUS":
                    item_id, note, tag = data
                    self.update_tree_item(item_id, {12: note}, tag) # Note = Index 12
                elif msg_type == "UPDATE_CRAWL":
                    item_id, info = data
                    # Update Post(8), Follow(9), Following(10)
                    self.update_tree_item(item_id, {8: info['post'], 9: info['followers'], 10: info['following']})
                elif msg_type == "SUCCESS":
                    item_id, key_2fa = data
                    self.success_count += 1
                    self.processed_count += 1
                    # Update 2FA(4), Note(12)
                    self.update_tree_item(item_id, {4: key_2fa, 12: "Success"}, "success")
                    self.update_stats_label()
                elif msg_type == "FAIL_CRITICAL":
                    item_id, err = data
                    self.processed_count += 1
                    self.fail_count += 1
                    # Update Post(8) = Err Code, Note(12) = Failed
                    self.update_tree_item(item_id, {8: err[:60], 12: "Failed"}, "error") 
                    self.update_stats_label()
                elif msg_type == "ALL_DONE":
                    self.is_running = False
                    self.btn_start.config(state="normal")
                    self.btn_stop.config(state="disabled", text="STOP")
                    self.status_var.set("Stopped / Finished")
                    messagebox.showinfo("Done", "Automation process finished.")
        except queue.Empty: pass
        self.root.after(100, self.process_queue)

    def update_tree_item(self, item_id, col_updates, tag=None):
        try:
            current_values = list(self.tree.item(item_id, "values"))
            for col_idx, val in col_updates.items(): current_values[col_idx] = val
            kw = {"values": current_values}
            if tag: kw["tags"] = (tag,)
            self.tree.item(item_id, **kw)
        except: pass

    def update_stats_label(self):
        self.lbl_progress.config(text=f"Progress: {self.processed_count}/{self.total_count}")
        self.lbl_success.config(text=f"Success: {self.success_count}")

    def export_data(self, mode):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text File", "*.txt")])
        if not filename: return
        count = 0
        with open(filename, "w", encoding="utf-8", newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            for item in self.tree.get_children():
                vals = self.tree.item(item)['values']
                note = vals[-1].lower()
                should_export = False
                if mode == "all": should_export = True
                elif mode == "success" and "success" in note: should_export = True
                elif mode == "failed" and ("fail" in note or "error" in note): should_export = True
                elif mode == "no_success" and "success" not in note: should_export = True
                if should_export:
                    writer.writerow(vals[:-1])
                    count += 1
        messagebox.showinfo("Export", f"Exported {count} items.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationGUI(root)
    root.mainloop()