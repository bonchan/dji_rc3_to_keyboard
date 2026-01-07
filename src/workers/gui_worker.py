import io
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
import queue
from src.utils.logger_setup import setup_logger
from src.utils.config_manager import load_config, save_config

class GUIWorker:
    def __init__(self, status_queue, shared_config, session_timestamp):
        self.logger = setup_logger("GUI_WORKER", session_timestamp)
        self.status_queue = status_queue    # For receiving heartbeats/images
        self.shared_config = shared_config  # For writing live settings
        self.config_data = dict(shared_config) # Initial local copy

    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title("Mission Control")
        self.root.geometry("900x600")

        # --- 1. THE MENU BAR ---
        menubar = tk.Menu(self.root)
        config_menu = tk.Menu(menubar, tearoff=0)
        config_menu.add_command(label="Open Configuration", command=self.show_config)
        config_menu.add_command(label="Show Camera Feed", command=self.show_display)
        menubar.add_cascade(label="Settings", menu=config_menu)
        self.root.config(menu=menubar)

        # --- 2. PERMANENT STATUS BAR (Always Visible at Top) ---
        status_bar = tk.Frame(self.root, relief="raised", bd=1)
        status_bar.pack(side="top", fill="x")

        # RC Status LED
        self.rc_status_canvas = tk.Canvas(status_bar, width=20, height=20, highlightthickness=0)
        self.rc_status_led = self.rc_status_canvas.create_oval(2, 2, 18, 18, fill="gray")
        self.rc_status_canvas.pack(side="left", padx=5)
        tk.Label(status_bar, text="RC Worker").pack(side="left", padx=(0, 20))

        # AI Status LED
        self.ai_status_canvas = tk.Canvas(status_bar, width=20, height=20, highlightthickness=0)
        self.ai_status_led = self.ai_status_canvas.create_oval(2, 2, 18, 18, fill="gray")
        self.ai_status_canvas.pack(side="left", padx=5)
        tk.Label(status_bar, text="AI Worker").pack(side="left")

        # --- 3. CONFIGURATION VIEW (Initially Hidden) ---
        self.config_frame = tk.Frame(self.root)
        
        # --- Drone Configuration Section ---
        drone_group = tk.LabelFrame(self.config_frame, text=" Drone Configuration ", padx=10, pady=10)
        drone_group.pack(fill="x", padx=20, pady=10)

        tk.Label(drone_group, text="Drone Serial Number:").pack(anchor="w")
        self.sn_var = tk.StringVar(value=self.config_data.get("drone_sn", ""))
        tk.Entry(drone_group, textvariable=self.sn_var).pack(fill="x", pady=(0, 10))

        tk.Label(drone_group, text="Project UUID:").pack(anchor="w")
        self.uuid_var = tk.StringVar(value=self.config_data.get("project_uuid", "f1"))
        tk.Entry(drone_group, textvariable=self.uuid_var).pack(fill="x", pady=(0, 10))

        tk.Label(drone_group, text="Organization Key:").pack(anchor="w")
        self.org_var = tk.StringVar(value=self.config_data.get("organization_key", ""))
        tk.Entry(drone_group, textvariable=self.org_var, show="*").pack(fill="x", pady=(0, 10))

        # --- AI Settings Section ---
        ai_group = tk.LabelFrame(self.config_frame, text=" AI Settings ", padx=10, pady=10)
        ai_group.pack(fill="x", padx=20, pady=10)

        tk.Label(ai_group, text="AI Confidence Threshold:").pack(anchor="w")
        self.conf_var = tk.DoubleVar(value=self.config_data.get("ai_confidence", 0.5))
        conf_slider = tk.Scale(ai_group, from_=0.0, to=1.0, resolution=0.05, 
                              orient="horizontal", variable=self.conf_var)
        conf_slider.pack(fill="x", pady=(0, 10))

        self.trigger_var = tk.BooleanVar(value=self.config_data.get("trigger_detection", True))
        tk.Checkbutton(ai_group, text="Enable Trigger Detection", variable=self.trigger_var).pack(anchor="w")

        # --- 4. CAPTURE AREA SECTION ---
        cap_frame = tk.LabelFrame(self.config_frame, text=" Capture Area (Ultra-Wide Optimization) ", padx=10, pady=10)
        cap_frame.pack(fill="x", padx=20, pady=10)

        self.left_var = tk.BooleanVar(value=self.shared_config.get("screen_left", True))
        self.right_var = tk.BooleanVar(value=self.shared_config.get("screen_right", True))

        tk.Checkbutton(cap_frame, text="Capture Left Half", variable=self.left_var).pack(side="left", padx=20)
        tk.Checkbutton(cap_frame, text="Capture Right Half", variable=self.right_var).pack(side="left", padx=20)

        # --- Controller Model ---
        model_group = tk.Frame(self.config_frame)
        model_group.pack(fill="x", padx=20, pady=10)
        tk.Label(model_group, text="Controller Model:").pack(side="left", padx=5)
        self.model_var = tk.StringVar(value=self.config_data.get("model_choice", "RC3"))
        combo = ttk.Combobox(model_group, textvariable=self.model_var)
        combo['values'] = ("RC3", "N1", "M300")
        combo.pack(side="left", fill="x", expand=True)
        
        # Save Button
        btn_save = tk.Button(self.config_frame, text="💾 SAVE & APPLY SETTINGS", 
                             bg="#007bff", fg="white", font=('Helvetica', 12, 'bold'),
                             command=self._save_and_close)
        btn_save.pack(pady=30, padx=50, fill="x")

        # --- 4. DISPLAY VIEW (Initially Visible) ---
        self.display_frame = tk.Frame(self.root, bg="black")
        self.display_frame.pack(fill="both", expand=True)

        self.img_label = tk.Label(self.display_frame, text="Waiting for Detection...", bg="black", fg="white")
        self.img_label.pack(fill="both", expand=True)

        # Start the background checker
        self.check_heartbeats()

    def _save_and_close(self):
        """Saves settings and switches back to camera feed"""
        self.save_and_broadcast()
        self.show_display()

    def show_config(self):
        """Switches to configuration view"""
        self.display_frame.pack_forget()
        self.config_frame.pack(fill="both", expand=True)

    def show_display(self):
        """Switches back to camera feed"""
        self.config_frame.pack_forget()
        self.display_frame.pack(fill="both", expand=True)

    def save_and_broadcast(self):
        if not self.left_var.get() and not self.right_var.get():
            tk.messagebox.showerror("Save Error", "You must select at least one capture area (Left or Right)!")
            return
        
        updated_config = {
            "drone_sn": self.sn_var.get(),
            "project_uuid": self.uuid_var.get(),
            "organization_key": self.org_var.get(),
            "model_choice": self.model_var.get(),
            "ai_confidence": self.conf_var.get(),
            "trigger_detection": self.trigger_var.get(),
            "screen_left": self.left_var.get(),
            "screen_right": self.right_var.get()
        }
        
        for key, value in updated_config.items():
            self.shared_config[key] = value
            
        save_config(updated_config)
        self.logger.info(f"⚙️ Shared Config updated and saved to disk.")

    def check_heartbeats(self):
        try:
            while True:
                msg = self.status_queue.get_nowait()
                
                # Handle Images
                if msg.get("status_update") == "DETECTION_SNAPSHOT":
                    img_bytes = msg.get("image")
                    count = msg.get("count", 0)
                    
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    w, h = pil_img.size
                    aspect = h / w
                    # Larger resize for the full-window view
                    new_w = 850
                    new_h = int(new_w * aspect)
                    pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    tk_img = ImageTk.PhotoImage(pil_img)
    
                    self.img_label.config(image=tk_img, text="")
                    self.img_label.image = tk_img 
                    self.logger.info(f"🖼️ GUI: Displaying detection ({count} objects)")

                # Handle Status LEDs
                if msg.get("status_update") in ["RC", "AI"]:
                    worker = msg["status_update"]
                    state = msg["state"]
                    color = "green" if state == "running" else "red"
                    
                    if worker == "RC":
                        self.rc_status_canvas.itemconfig(self.rc_status_led, fill=color)
                    elif worker == "AI":
                        self.ai_status_canvas.itemconfig(self.ai_status_led, fill=color)
                        
        except queue.Empty:
            pass
        self.root.after(500, self.check_heartbeats)

    def run(self):
        self.setup_ui()
        self.root.mainloop()

def run_gui_worker(status_queue, shared_config, session_timestamp):
    app = GUIWorker(status_queue, shared_config, session_timestamp)
    app.run()