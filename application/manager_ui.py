import os
from pathlib import Path
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from controller import Controller
import json


class UIManager:
    def __init__(self, root):
        self.root = root
        self.method_widgets = {}
        self.view_canvases = {}
        self.current_display_size = None
        self.rgb_photo = None
        self.method_photos = {}
        self.method_cbar = {}
        self.method_photos_png = {}
        self.method_cbar_png = {}
        self.lock_state = False
        self.sync_values = {'min': '', 'max': ''}
        self.disp_path = {}
        self.min_max_entry = {}
        self.vis_min = {}
        self.vis_max = {}
        self.lock_buttons = {}
        self.reset_min_max_buttons = {}
        self.fullscreen_windows = {}
        self.fullscreen_buttons = {}
        
        # Zoom and pan attributes
        self.zoom_level = 1.0
        self.zoom_factor = 1.2
        self.max_zoom_level = 5.0
        self.min_zoom_level = 1.0
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.canvas_width = 0
        self.canvas_height = 0
        self.is_panning = False
        
        # Initialize camera parameters
        self.vis_mode = ttk.StringVar(value="disp")
        self.mode_changed = False
        self.vis_mode.trace_add("write", lambda *args: setattr(self, 'mode_changed', True))
        self.cx0_var = ttk.DoubleVar(value=0.0)
        self.cx1_var = ttk.DoubleVar(value=0.0)
        self.focal_var = ttk.DoubleVar(value=0.0)
        self.baseline_var = ttk.DoubleVar(value=0.0)
        self.color_map_var = ttk.StringVar(value='RdBu')
        self.status_var = ttk.StringVar(value="Status: Ready")
        
        self.controller = Controller(self)
        
        self._setup_window()
        self._create_frames()
        self._bottom_frame()
        self._create_image_grid()
        self._status_frame()

    def _setup_window(self):
        self.root.title("Depth Player")
        self.root.geometry("1200x800")
        self.root.grid_rowconfigure(0, weight=20)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

    def _create_frames(self):
        self.top_frame = ttk.Frame(self.root)
        self.top_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.right_frame = ttk.Frame(self.root)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        self.status_frame = ttk.Frame(self.root, height=30)
        self.status_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

    def _bottom_frame(self):
        self.bottom_frame.columnconfigure(0, weight=1)
        self.bottom_frame.columnconfigure(1, weight=1)
        self.bottom_frame.columnconfigure(2, weight=1)
        self.bottom_frame.columnconfigure(3, weight=1)
        
        controls_frame = ttk.Frame(self.bottom_frame)
        controls_frame.grid(row=0, column=0, columnspan=4, sticky="nsew", pady=10)
        
        playback_frame = ttk.Frame(controls_frame)
        playback_frame.pack(fill=X, pady=2)
        
        self.play_button = ttk.Button(playback_frame, text="▶", command=self.controller.toggle_play)
        self.play_button.pack(side=LEFT, padx=2)

        reset_button = ttk.Button(playback_frame, text="↻", command=self.controller.reset_app)
        reset_button.pack(side=LEFT, padx=2)
        
        backward_10_frame_button = ttk.Button(
            playback_frame,
            text="<<",
            command=lambda nbr_frames=-10: self.controller.skip_frames(nbr_frames)
        )
        backward_10_frame_button.pack(side=LEFT, padx=2)

        backward_1_frame_button = ttk.Button(
            playback_frame,
            text="<",
            command=lambda nbr_frames=-1: self.controller.skip_frames(nbr_frames)
        )
        backward_1_frame_button.pack(side=LEFT, padx=2)

        forward_1_frame_button = ttk.Button(
            playback_frame,
            text=">",
            command=lambda nbr_frames=1: self.controller.skip_frames(nbr_frames)
        )
        forward_1_frame_button.pack(side=LEFT, padx=2)

        forward_10_frame_button = ttk.Button(
            playback_frame,
            text=">>",
            command=lambda nbr_frames=10: self.controller.skip_frames(nbr_frames)
        )
        forward_10_frame_button.pack(side=LEFT, padx=2)
        
        slider_frame = ttk.Frame(controls_frame)
        slider_frame.pack(fill=X, pady=0)
        
        ttk.Label(slider_frame, text="Frame Index:").pack(side=LEFT)
        self.slider = ttk.Scale(
            slider_frame, from_=0, to=100, orient=HORIZONTAL, length=600,
            command=self.controller.on_slider_move
        )
        self.slider.pack(side=LEFT, fill=X, expand=True)
        
        self.frame_index_label = ttk.Label(slider_frame, text="0/0")
        self.frame_index_label.pack(side=LEFT, padx=10)
        
        self.method_params = ttk.LabelFrame(self.bottom_frame, text="Visualisation range", padding=2)
        self.method_params.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        
        for i, method in enumerate(self.controller.methods):
            frame = ttk.Frame(self.method_params)
            frame.pack(fill=X, pady=0)
            
            if method in self.controller.default_min_max:
                if not self.controller.is_depth_mode:
                    min_val = self.controller.default_min_max[method].get('disp_min', 0.0)
                    max_val = self.controller.default_min_max[method].get('disp_max', 0.0)
                else:
                    min_val = self.controller.default_min_max[method].get('depth_min', 0.0)
                    max_val = self.controller.default_min_max[method].get('depth_max', 0.0)
            else:
                min_val = 0.0
                max_val = 0.0
            
            min_var = ttk.DoubleVar(value=min_val)
            max_var = ttk.DoubleVar(value=max_val)
            
            if i == 0:
                min_var.trace_add("write", lambda *args, m=method: self.controller.on_first_method_change(m, is_min=True))
                max_var.trace_add("write", lambda *args, m=method: self.controller.on_first_method_change(m, is_min=False))
            
            ttk.Label(frame, text=method, width=18).pack(side=LEFT)
            min_entry = ttk.Entry(frame, width=5, textvariable=min_var)
            min_entry.pack(side=LEFT, padx=1, pady=0.5)
            max_entry = ttk.Entry(frame, width=5, textvariable=max_var)
            max_entry.pack(side=LEFT, padx=1, pady=0.5)
            
            if i == 0:
                reset_min_max = ttk.Button(frame, text="from min/max", width=11, 
                                        command=lambda m=method: self.controller.reset_min_max(m))
                reset_min_max.pack(side=LEFT, padx=1, pady=0.5)
            else:
                reset_min_max = ttk.Button(frame, text="from min/max", width=11, 
                                         command=lambda m=method: self.controller.reset_min_max(m))
                reset_min_max.pack(side=LEFT, padx=1, pady=0.5)
                self.reset_min_max_buttons[method] = reset_min_max
                lock_button = ttk.Button(frame, text="Unlocked", width=8, 
                                       command=lambda m=method: self.controller.toggle_lock(m))
                lock_button.pack(side=LEFT, padx=1, pady=0.5)
                self.lock_buttons[method] = lock_button
                
            self.method_widgets[method] = {'min': min_var, 'max': max_var}
            self.min_max_entry[method] = {
                'min_entry': min_var,
                'max_entry': max_var,
                'min_entry_widget': min_entry,
                'max_entry_widget': max_entry
            }
            
            min_entry.bind('<FocusOut>', 
                lambda e, m=method, min_var=min_var, max_var=max_var: self._validate_min_max(m, min_var, max_var))
            max_entry.bind('<FocusOut>', 
                lambda e, m=method, min_var=min_var, max_var=max_var: self._validate_min_max(m, min_var, max_var))
            min_entry.bind('<FocusOut>', lambda e, m=method: self.update_sync(m))
            max_entry.bind('<FocusOut>', lambda e, m=method: self.update_sync(m))
        
        self.cam_params = ttk.LabelFrame(self.bottom_frame, text="Mode", padding=2)
        self.cam_params.grid(row=1, column=1, sticky="nsew", padx=2)

        self.cam_params.columnconfigure(0, weight=1)
        self.cam_params.columnconfigure(1, weight=1)
        self.cam_params.rowconfigure(0, weight=1, pad=1)
        self.cam_params.rowconfigure(1, weight=1, pad=1)
        self.cam_params.rowconfigure(2, weight=1, pad=1)

        mode_frame = ttk.Frame(self.cam_params)
        mode_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=0)
        ttk.Radiobutton(mode_frame, text="Disp", variable=self.vis_mode, 
                        command=self._on_vis_mode_change, value="disp", width=6).pack(side=LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text="Depth", variable=self.vis_mode, 
                        command=self._on_vis_mode_change, value="depth", width=6).pack(side=LEFT, padx=2)

        params = [
            [("cx0:", self.cx0_var), ("cx1:", self.cx1_var)],
            [("Focal length:", self.focal_var), ("Baseline:", self.baseline_var)]
        ]

        for row_idx, row_params in enumerate(params, start=1):
            for col_idx, (text, var) in enumerate(row_params):
                frame = ttk.Frame(self.cam_params, padding=0)
                frame.grid(row=row_idx, column=col_idx, sticky="ew", padx=1, pady=0)
                
                ttk.Label(frame, text=text, width=10).pack(side=LEFT, padx=1)
                entry = ttk.Entry(frame, textvariable=var, width=5)
                entry.pack(side=LEFT, fill=X, padx=2, expand=True)
                entry.bind('<FocusOut>', lambda e, v=var, n=text: self._validate_positive(v, n.strip(':')))
        
        self._on_vis_mode_change()
        
        self.vis_controls = ttk.LabelFrame(self.bottom_frame, text="Visualization", padding=2)
        self.vis_controls.grid(row=1, column=2, sticky="nsew", padx=2, pady=2)
        
        color_maps = ['RdBu', 'plasma', 'plasma_r', 'magma', 'magma_r', 'viridis', 
                     'cividis', 'inferno', 'turbo', 'cubehelix', 'coolwarm', 'seismic', 'bwr']
        cmap_combobox = ttk.Combobox(
            self.vis_controls,
            textvariable=self.color_map_var,
            values=color_maps,
            state='readonly',
            width=6
        )
        cmap_combobox.pack(fill=X, padx=3, pady=0)
        
        zoom_frame = ttk.Frame(self.vis_controls)
        zoom_frame.pack(fill=X, pady=0)
        ttk.Button(zoom_frame, text="Zoom In", command=self.zoom_in, bootstyle="info").pack(side=LEFT, padx=4, pady=3)
        ttk.Button(zoom_frame, text="Zoom Out", command=self.zoom_out, bootstyle="info").pack(side=LEFT, padx=4, pady=3)
        ttk.Button(zoom_frame, text="Reset", command=self.reset_zoom, bootstyle="warning").pack(side=LEFT, padx=4, pady=3)
        
        self.methods_frame = ttk.LabelFrame(self.bottom_frame, text="Updates", padding=2)
        self.methods_frame.grid(row=1, column=3, sticky="nsew", padx=2, pady=2)
        
        ttk.Button(
            self.methods_frame,
            text="Update parameters",
            command=self.controller._update_visualization,
            bootstyle="primary",
            width=10
        ).pack(fill=X, padx=3, pady=3)
        
        ttk.Button(
            self.methods_frame,
            text="Update methods",
            command=self._start_DataEntryMethod,
            bootstyle="primary",
            width=10
        ).pack(fill=X, padx=3, pady=3)

    def _status_frame(self):
        ttk.Label(
            self.status_frame,
            textvariable=self.status_var,
            bootstyle="secondary"
        ).pack(side=LEFT, padx=5, pady=2)

    def _on_vis_mode_change(self, *args):
        is_depth_mode = self.vis_mode.get() == "depth"
        
        cx0_entry = self.cam_params.grid_slaves(row=1, column=0)[0].winfo_children()[1]
        cx1_entry = self.cam_params.grid_slaves(row=1, column=1)[0].winfo_children()[1]
        focal_entry = self.cam_params.grid_slaves(row=2, column=0)[0].winfo_children()[1]
        baseline_entry = self.cam_params.grid_slaves(row=2, column=1)[0].winfo_children()[1]
        
        state = 'normal' if is_depth_mode else 'disabled'
        cx0_entry.config(state=state)
        cx1_entry.config(state=state)
        focal_entry.config(state=state)
        baseline_entry.config(state=state)
        
        self.controller.is_depth_mode = is_depth_mode

    def update_frame_index(self, current_idx, total_frames):
        self.frame_index_label.config(text=f"{current_idx}/{total_frames}")

    def on_mousewheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.zoom_in()
        elif event.num == 5 or event.delta < 0:
            self.zoom_out()

    def zoom_in(self):
        if not hasattr(self, 'rgb_image') and not any(method in self.method_photos_png for method in self.controller.methods):
            messagebox.showwarning("Warning", "No images loaded to zoom")
            return
        
        if self.zoom_level >= self.max_zoom_level:
            return
            
        self.zoom_level = min(self.zoom_level * self.zoom_factor, self.max_zoom_level)
        self._update_status(f"Zoom: {self.zoom_level:.1f}x")
        self._apply_zoom_pan_to_all()

    def zoom_out(self):
        if not hasattr(self, 'rgb_image') and not any(method in self.method_photos_png for method in self.controller.methods):
            messagebox.showwarning("Warning", "No images loaded to zoom")
            return
        
        if self.zoom_level <= self.min_zoom_level:
            self.zoom_level = self.min_zoom_level
            self.image_offset_x = 0
            self.image_offset_y = 0
        else:
            self.zoom_level = max(self.zoom_level / self.zoom_factor, self.min_zoom_level)
        
        self._update_status(f"Zoom: {self.zoom_level:.1f}x")
        self._apply_zoom_pan_to_all()

    def reset_zoom(self):
        if not hasattr(self, 'rgb_image') and not any(method in self.method_photos_png for method in self.controller.methods):
            return
        
        self.zoom_level = 1.0
        self.image_offset_x = 0
        self.image_offset_y = 0
        self._update_status("Zoom reset")
        self._apply_zoom_pan_to_all()

    def _apply_zoom_pan_to_all(self):
        try:
            min_width = min(canvas.winfo_width() for canvas in self.method_canvases.values() if canvas.winfo_width() > 1)
            min_height = min(canvas.winfo_height() for canvas in self.method_canvases.values() if canvas.winfo_height() > 1)
            
            if hasattr(self, 'rgb_image') and self.rgb_image:
                self._resize_rgb_image(min_width, min_height)
            
            for method_name in self.controller.methods:
                if (method_name in self.method_canvases and 
                    method_name in self.method_photos_png and 
                    self.method_photos_png[method_name] is not None):
                    
                    data = self.method_photos_png[method_name]
                    cbar = self.method_cbar_png.get(method_name)
                    
                    self._display_method_data(
                        method_name, 
                        data,
                        cbar,
                        min_width,
                        min_height
                    )
        except Exception as e:
            print(f"Error applying zoom/pan: {str(e)}")

    def start_pan(self, event):
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.is_panning = True
        for canvas in self.method_canvases.values():
            canvas.config(cursor="fleur")

    def do_pan(self, event):
        if not self.is_panning:
            return
            
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        if hasattr(self, 'current_display_size') and self.current_display_size:
            max_offset_x = max(0, (self.current_display_size[0] * self.zoom_level - self.canvas_width)) // 2
            max_offset_y = max(0, (self.current_display_size[1] * self.zoom_level - self.canvas_height)) // 2
            
            self.image_offset_x = max(-max_offset_x, min(self.image_offset_x + dx, max_offset_x))
            self.image_offset_y = max(-max_offset_y, min(self.image_offset_y + dy, max_offset_y))
        
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self._apply_zoom_pan_to_all()

    def end_pan(self, event):
        self.is_panning = False
        for canvas in self.method_canvases.values():
            canvas.config(cursor="")

    def _on_canvas_resize(self, method_name):
        if method_name == "RGB":
            self._resize_rgb_image()
        elif (method_name in self.method_photos_png and 
              method_name in self.method_cbar_png):
            self._display_method_data(
                method_name, 
                self.method_photos_png[method_name],
                self.method_cbar_png[method_name]
            )

    def _validate_min_max(self, method, min_var, max_var):
        try:
            min_val = min_var.get()
            max_val = max_var.get()
            
            if min_val >= max_val:
                messagebox.showerror("Validation Error", 
                    f"Max value must be greater than min value for {method}")
                max_var.set(min_val + 1.0)
                return False
            return True
        except:
            messagebox.showerror("Validation Error", "Please enter valid numbers")
            return False

    def _validate_positive(self, var, name):
        try:
            val = var.get()
            if val < 0:
                messagebox.showerror("Validation Error",
                    f"{name} cannot be negative")
                var.set(abs(val))
                return False
            return True
        except:
            messagebox.showerror("Validation Error", 
                f"Please enter a valid number for {name}")
            return False        
        
    def update_sync(self, changed_method):
        if self.lock_state:
            self.sync_values['min'] = self.method_widgets[changed_method]['min'].get()
            self.sync_values['max'] = self.method_widgets[changed_method]['max'].get()
            self.apply_sync()
            
    def apply_sync(self):
        if self.lock_state:
            for method in self.method_widgets:
                self.method_widgets[method]['min'].set(self.sync_values['min'])
                self.method_widgets[method]['max'].set(self.sync_values['max'])
    
    def _display_rgb_image(self, img):
        try:
            self.rgb_image = img
            self._resize_rgb_image()
        except Exception as e:
            raise Exception(f"Failed to display image sequence: {str(e)}")

    def _resize_rgb_image(self, canvas_width=None, canvas_height=None):
        if not hasattr(self, 'rgb_image') or self.rgb_image is None:
            return
            
        if canvas_width is None:
            canvas_width = self.rgb_canvas.winfo_width()
        if canvas_height is None:
            canvas_height = self.rgb_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
            
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        
        img_ratio = self.rgb_image.width / self.rgb_image.height
        canvas_ratio = canvas_width / canvas_height
        
        if canvas_ratio > img_ratio:
            base_height = canvas_height
            base_width = int(base_height * img_ratio)
        else:
            base_width = canvas_width
            base_height = int(base_width / img_ratio)
        
        display_width = int(base_width * self.zoom_level)
        display_height = int(base_height * self.zoom_level)
        
        self.current_display_size = (display_width, display_height)
        
        resized_img = self.rgb_image.resize((display_width, display_height), Image.LANCZOS)
        self.rgb_photo = ImageTk.PhotoImage(resized_img)
        
        self.rgb_canvas.delete("all")
        
        x_pos = canvas_width//2 + self.image_offset_x
        y_pos = canvas_height//2 + self.image_offset_y
        
        self.rgb_canvas.create_image(x_pos, y_pos, image=self.rgb_photo, anchor=CENTER)
        
        if self.zoom_level > 1.0:
            self.rgb_canvas.bind("<ButtonPress-1>", self.start_pan)
            self.rgb_canvas.bind("<B1-Motion>", self.do_pan)
            self.rgb_canvas.bind("<ButtonRelease-1>", self.end_pan)
        else:
            self.rgb_canvas.unbind("<ButtonPress-1>")
            self.rgb_canvas.unbind("<B1-Motion>")
            self.rgb_canvas.unbind("<ButtonRelease-1>")

    def _display_method_data(self, method_name, data, cbar, canvas_width=None, canvas_height=None):
        try:
            canvas = self.method_canvases.get(method_name)
            cbar_canvas = self.cbar_canvases.get(method_name)
            if not canvas or not cbar_canvas:
                return
                
            if canvas_width is None:
                canvas_width = canvas.winfo_width()
            if canvas_height is None:
                canvas_height = canvas.winfo_height()
            cbar_width = cbar_canvas.winfo_width()
            cbar_height = cbar_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                return
                
            self.method_photos_png[method_name] = data
            self.method_cbar_png[method_name] = cbar
                
            img_ratio = data.width / data.height
            canvas_ratio = canvas_width / canvas_height
            
            if canvas_ratio > img_ratio:
                base_height = canvas_height
                base_width = int(base_height * img_ratio)
            else:
                base_width = canvas_width
                base_height = int(base_width / img_ratio)
            
            display_width = int(base_width * self.zoom_level)
            display_height = int(base_height * self.zoom_level)
            
            resized_img = data.resize((display_width, display_height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(resized_img)
            self.method_photos[method_name] = photo
            
            cbar_height = canvas_height
            resized_cbar = cbar.resize((50, cbar_height), Image.LANCZOS)
            cbar_img = ImageTk.PhotoImage(resized_cbar)
            self.method_cbar[method_name] = cbar_img
            
            canvas.delete("all")
            cbar_canvas.delete("all")
            
            image_x = canvas_width // 2 + self.image_offset_x
            image_y = canvas_height // 2 + self.image_offset_y
            
            cbar_x = cbar_width // 2
            cbar_y = cbar_height // 2
            
            canvas.create_image(image_x, image_y, image=photo, anchor=CENTER)
            cbar_canvas.create_image(cbar_x, cbar_y, image=cbar_img, anchor=CENTER)
            
            if self.zoom_level > 1.0:
                canvas.bind("<ButtonPress-1>", self.start_pan)
                canvas.bind("<B1-Motion>", self.do_pan)
                canvas.bind("<ButtonRelease-1>", self.end_pan)
            else:
                canvas.unbind("<ButtonPress-1>")
                canvas.unbind("<B1-Motion>")
                canvas.unbind("<ButtonRelease-1>")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to display {method_name} data: {str(e)}")

    def update_frames(self):
        if hasattr(self, 'rgb_image') and self.rgb_image:
            self._resize_rgb_image()
            
        for method_name in self.controller.methods:
            if (method_name in self.method_photos_png and 
                method_name in self.method_cbar_png and
                self.method_photos_png[method_name] is not None and
                self.method_cbar_png[method_name] is not None):
                
                self._display_method_data(
                    method_name, 
                    self.method_photos_png[method_name],
                    self.method_cbar_png[method_name]
                )

    def _start_DataEntryMethod(self, method_name=None, npy_disp=None, npz_disp=None, is_update=False):
        self.DataEntryMethod(self)
    
    def refresh_ui(self):
        for widget in self.bottom_frame.winfo_children():
            widget.destroy()
        for widget in self.top_frame.winfo_children():
            widget.destroy()
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        
        self._bottom_frame()
        self._create_image_grid()
        
    def set_controller(self, controller):
        self.controller = controller
        
    def _update_status(self, message):
        zoom_info = f" Zoom: {self.zoom_level:.1f}x" if hasattr(self, 'zoom_level') else ""
        self.status_var.set(f"Status: {message}{zoom_info}")
        
    def _handle_upload(self, target, file_path):
        if not file_path:
            return
        
        try:
            if target == "RGB":
                img = self.controller.load_rgb_image(file_path)
                self._display_rgb_image(img)
                self._update_status(f"Loaded image sequence: {os.path.basename(file_path)}")
            else:
                data, cbar = self.controller.load_method_data(target, file_path)
                self.disp_path[target] = file_path
                self.method_photos_png[target] = data
                self.method_cbar_png[target] = cbar
                self._display_method_data(target, data, cbar)
                self._update_status(f"Loaded {target} disparity/depth: {os.path.basename(file_path)}")
                
                if target in self.fullscreen_buttons:
                    self.fullscreen_buttons[target].config(state='normal')
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
            self._update_status(f"Error loading {target} data")
        
    def _create_image_grid(self):
        grid_frame = ttk.Frame(self.top_frame)
        grid_frame.pack(fill=BOTH, expand=True, padx=0, pady=0)
        
        grid_frame.rowconfigure(0, weight=1)
        grid_frame.rowconfigure(1, weight=1)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        
        frames = [
            ("image sequence", "RGB", (0, 0))
        ]
        
        for i, method in enumerate(self.controller.methods):
            if i >= 3:
                break
            positions = [(0, 1), (1, 0), (1, 1)]
            frames.append((method, method, positions[i]))
        
        self.method_canvases = {}
        self.cbar_canvases = {}
        self.fullscreen_windows = {}
        
        for title, method_name, (row, col) in frames:
            frame = ttk.LabelFrame(grid_frame, text=title, padding=10)
            frame.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")
            
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            frame.columnconfigure(1, weight=0)
            
            canvas = ttk.Canvas(frame, bg='white')
            canvas.grid(row=0, column=0, sticky="nsew")
            
            cbar_canvas = ttk.Canvas(frame, bg='white', width=50)
            cbar_canvas.grid(row=0, column=1, sticky="ns")
            
            canvas.bind("<Configure>", lambda e, m=method_name: self._on_canvas_resize(m))
            
            btn_frame = ttk.Frame(frame)
            btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
            
            if method_name == "RGB":
                btn_text = "Upload image sequence"
                self.rgb_canvas = canvas
                ttk.Button(
                    btn_frame,
                    text=btn_text,
                    command=lambda m=method_name: self.controller._upload_all_files(m),
                    bootstyle="info"
                ).pack(side=LEFT, pady=1)
            else:
                btn_text = f"Upload {method_name} Data"
                ttk.Button(
                    btn_frame,
                    text=btn_text,
                    command=lambda m=method_name: self.controller._upload_all_files(m),
                    bootstyle="info"
                ).pack(side=LEFT, pady=1)
                
                fullscreen_btn = ttk.Button(
                    btn_frame,
                    text="Fullscreen",
                    command=lambda m=method_name: self.show_fullscreen(m),
                    bootstyle="success",
                    width=8,
                )
                fullscreen_btn.pack(side=LEFT, padx=2)
                
                self.vis_min[method_name] = ttk.Label(btn_frame, text="")
                self.vis_min[method_name].pack(side=LEFT, padx=2)
                self.vis_max[method_name] = ttk.Label(btn_frame, text="")
                self.vis_max[method_name].pack(side=LEFT, padx=2)
                
                self.fullscreen_buttons[method_name] = fullscreen_btn
            
            self.method_canvases[method_name] = canvas
            self.cbar_canvases[method_name] = cbar_canvas
            
            canvas.bind("<ButtonPress-1>", self.start_pan)
            canvas.bind("<B1-Motion>", self.do_pan)
            canvas.bind("<ButtonRelease-1>", self.end_pan)
            canvas.bind("<MouseWheel>", self.on_mousewheel)
            canvas.bind("<Button-4>", self.on_mousewheel)
            canvas.bind("<Button-5>", self.on_mousewheel)

    def show_fullscreen(self, method_name):
        try:
            if (method_name not in self.method_photos_png or 
                self.method_photos_png[method_name] is None):
                messagebox.showwarning("Warning", f"No {method_name} data loaded")
                return
            
            vis_window = ttk.Toplevel(self.root)
            vis_window.title(f"{method_name} Visualization")
            vis_window.geometry("800x600")
            
            container = ttk.Frame(vis_window)
            container.pack(fill=BOTH, expand=True)
            
            vis_canvas = ttk.Canvas(container, bg='white')
            vis_canvas.pack(side=LEFT, fill=BOTH, expand=True)
            
            cbar_canvas = ttk.Canvas(container, bg='white', width=50)
            cbar_canvas.pack(side=RIGHT, fill=Y)
            
            zoom_state = {
                'level': 1.0,
                'offset_x': 0,
                'offset_y': 0,
                'pan_start': None
            }
            
            def display_visualization():
                try:
                    width = vis_canvas.winfo_width()
                    height = vis_canvas.winfo_height()
                    
                    if width <= 1 or height <= 1:
                        return
                    
                    img = self.method_photos_png[method_name]
                    img_ratio = img.width / img.height
                    canvas_ratio = width / height
                    
                    if canvas_ratio > img_ratio:
                        disp_height = height
                        disp_width = int(disp_height * img_ratio)
                    else:
                        disp_width = width 
                        disp_height = int(disp_width / img_ratio)
                    
                    disp_width = int(disp_width * zoom_state['level'])
                    disp_height = int(disp_height * zoom_state['level'])
                    
                    resized_img = img.resize((disp_width, disp_height), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(resized_img)
                    
                    cbar_img = self.method_cbar_png[method_name]
                    cbar_resized = cbar_img.resize((50, height), Image.LANCZOS)
                    cbar_photo = ImageTk.PhotoImage(cbar_resized)
                    
                    vis_canvas.delete("all")
                    cbar_canvas.delete("all")
                    
                    img_x = width//2 + zoom_state['offset_x']
                    img_y = height//2 + zoom_state['offset_y']
                    
                    vis_canvas.create_image(img_x, img_y, image=photo, anchor=CENTER)
                    cbar_canvas.create_image(25, height//2, image=cbar_photo, anchor=CENTER)
                    
                    vis_canvas.image = photo
                    cbar_canvas.image = cbar_photo
                    
                except Exception as e:
                    messagebox.showerror("Display Error", f"Failed to display visualization: {str(e)}")
            
            def on_pan_start(event):
                zoom_state['pan_start'] = (event.x, event.y)
                vis_canvas.config(cursor="fleur")
            
            def on_pan_move(event):
                if zoom_state['pan_start']:
                    dx = event.x - zoom_state['pan_start'][0]
                    dy = event.y - zoom_state['pan_start'][1]
                    zoom_state['offset_x'] += dx
                    zoom_state['offset_y'] += dy
                    zoom_state['pan_start'] = (event.x, event.y)
                    display_visualization()
            
            def on_pan_end(event):
                zoom_state['pan_start'] = None
                vis_canvas.config(cursor="")
            
            def on_mousewheel(event):
                zoom_factor = 1.2
                if event.num == 4 or event.delta > 0:
                    zoom_state['level'] = min(zoom_state['level'] * zoom_factor, 5.0)
                elif event.num == 5 or event.delta < 0:
                    zoom_state['level'] = max(zoom_state['level'] / zoom_factor, 1.0)
                    if zoom_state['level'] == 1.0:
                        zoom_state['offset_x'] = 0
                        zoom_state['offset_y'] = 0
                display_visualization()
            
            vis_canvas.bind("<ButtonPress-1>", on_pan_start)
            vis_canvas.bind("<B1-Motion>", on_pan_move)
            vis_canvas.bind("<ButtonRelease-1>", on_pan_end)
            vis_canvas.bind("<MouseWheel>", on_mousewheel)
            vis_canvas.bind("<Button-4>", on_mousewheel)
            vis_canvas.bind("<Button-5>", on_mousewheel)
            
            vis_window.after(100, display_visualization)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open visualization window: {str(e)}")

    class DataEntryMethod:
        def __init__(self, ui):
            self.ui = ui
            self.controller = ui.controller
            self.top = ttk.Toplevel(self.ui.root)
            self.top.title("Manage Methods")
            self.top.geometry("800x180")
            
            main_frame = ttk.Frame(self.top)
            main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
            
            list_frame = ttk.Frame(main_frame)
            list_frame.pack(side=LEFT, fill=BOTH, expand=True)
            
            ttk.Label(list_frame, text="Available Methods:").pack(pady=5)
            self.methods_listbox = tk.Listbox(list_frame, height=15, width=30)
            self.methods_listbox.pack(fill=BOTH, expand=True, padx=5, pady=5)
            
            details_frame = ttk.LabelFrame(main_frame, text="Method Details", padding=10)
            details_frame.pack(side=RIGHT, fill=BOTH, expand=True)
            
            ttk.Label(details_frame, text="Method Name:").grid(row=0, column=0, sticky=W, pady=5)
            self.name_var = tk.StringVar()
            self.name_entry = ttk.Entry(details_frame, textvariable=self.name_var, width=30)
            self.name_entry.grid(row=0, column=1, columnspan=2, sticky=EW, pady=5)
            
            ttk.Label(details_frame, text="Default Path:").grid(row=1, column=0, sticky=W, pady=5)
            self.path_var = tk.StringVar()
            self.path_entry = ttk.Entry(details_frame, textvariable=self.path_var, width=40)
            self.path_entry.grid(row=1, column=1, sticky=EW, pady=5)
            
            
            button_frame = ttk.Frame(details_frame)
            button_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky=E)
            
            ttk.Button(
                button_frame,
                text="Update",
                command=self._update_method,
                bootstyle="info"
            ).pack(side=LEFT, padx=5)
            ttk.Button(
                button_frame,
                text="Close",
                command=self.top.destroy,
                bootstyle="secondary"
            ).pack(side=RIGHT, padx=5)
            
            self._load_methods()
            self.selection = None
            self.methods_listbox.bind('<<ListboxSelect>>', self._on_method_select)
        
        def _load_methods(self):
            self.methods_listbox.delete(0, tk.END)
            for method in self.controller.methods:
                self.methods_listbox.insert(tk.END, method)
        
        def _on_method_select(self, event):
            selection = self.methods_listbox.curselection()
            if selection:
                self.selection = selection[0]
                method_name = self.methods_listbox.get(self.selection)
                if method_name in self.controller.methods:
                    self.name_var.set(method_name)
                    self.path_var.set(self.controller.default_paths[self.controller.methods.index(method_name)])
        
        def _update_method(self):
            if self.selection is None:
                messagebox.showerror("Error", "No method selected")
                return
                
            old_name = self.methods_listbox.get(self.selection)
            new_name = self.name_var.get()
            
            if not new_name:
                messagebox.showerror("Error", "Method name is required")
                return
            
            if new_name != old_name and new_name in self.controller.methods:
                messagebox.showerror("Error", "Method name already exists")
                return
            
            default_path = self.path_var.get()
            if not self.controller.validate_path(default_path):
                messagebox.showerror("Error", "Invalid default path")
                return
                
            self.controller.update_method(old_name, new_name, default_path)
            self._load_methods()
            self._clear_fields()
            self.ui.refresh_ui()
            self.top.destroy()
        
        def _clear_fields(self):
            self.name_var.set("")
            self.path_var.set("")