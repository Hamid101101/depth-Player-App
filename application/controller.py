import os, sys
import re
import json
import io
import gc
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import seaborn as sns


class Controller:
    def __init__(self, ui):
        self.ui = ui
        self.ui.set_controller(self)
        self.path_compared_methods = self.resource_path('./assets/compared_methods.json')
        self.path_parameters = self.resource_path('./assets/parameters.json')
        self.methods, self.default_paths = self._read_methods(self.path_compared_methods)
        self.default_min_max = {}
        self._read_parameters(self.path_parameters)
        self.current_color_map = 'viridis'
        self.rgb_image = None 
        self.method_depth_data = {}
        self.method_disp_data = {}
        self.sorted_files = {}
        self.total_frames = 0
        self.current_frame = 0
        self.is_playing = False
        self.lock_state = {}
        for im, m in enumerate(self.methods):
            self.lock_state[m] = False
        self.locked_min_max = {}
        self.frame_min_max = {}
        
    def resource_path(self, relative_path):
        """ Get absolute path to resource (works for dev and PyInstaller) """
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)
        
    def _read_methods(self, path):
        file_path = Path(path)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        method_names = []
        default_paths = []
        
        for method_entry in data['methods']:
            method_names.append(method_entry['name'])
            default_paths.append(method_entry['default_path'])
        
        return method_names, default_paths

    def _read_parameters(self, path):
        file_path = Path(path)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.is_depth_mode = data['is_depth_mode']
    
        for method in self.methods:
            if not self.is_depth_mode:
                self.default_min_max[method] = {'disp_min': data[method]['min'], 'disp_max': data[method]['max']}
            else:
                self.default_min_max[method] = {'depth_min': data[method]['min'], 'depth_max': data[method]['max']}
                
        self.ui.cx0_var = ttk.DoubleVar(value=data['cx0'])
        self.ui.cx1_var = ttk.DoubleVar(value=data['cx1'])
        self.ui.color_map_var = ttk.StringVar(value=data['color_map'])
        self.ui.focal_var = ttk.DoubleVar(value=data['focal_lenght'])
        self.ui.baseline_var = ttk.DoubleVar(value=data['baseline'])
        self.ui.vis_mode = ttk.StringVar(value= 'depth' if self.is_depth_mode else 'disp')
        
    
    def get_method_data(self, method_name):
        with open(self.path_compared_methods, 'r') as f:
            data = json.load(f)
        
        for method in data["methods"]:
            if method_name in method:
                return method[method_name]
        return None
        
    def update_method(self, old_name, new_name, new_path):
        if old_name not in self.methods:
            raise ValueError("Method not found")
            
        if not self.is_valid_method_name(new_name):
            raise ValueError("Invalid method name")
            
        if not self.validate_path(new_path):
            raise ValueError("Invalid default path")
            
        if new_name != old_name and new_name in self.methods:
            raise ValueError("Method name already exists")
            
        index = self.methods.index(old_name)
        self.methods[index] = new_name
        self.default_paths[index] = new_path
        
        if new_name != old_name:
            self.default_min_max[new_name] = self.default_min_max.pop(old_name)
            self.lock_state[new_name] = self.lock_state.pop(old_name)
            
        self._save_methods_config()
        
        return True
        
    def is_valid_method_name(self, name):
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, name)) and len(name) <= 50

    def validate_path(self, path):
        #path = Path(path)
        #try:
        #    return path.exists() and os.access(path, os.R_OK)
        #except (TypeError, ValueError):
        #    return False
        return True
        
    def _save_methods_config(self):
        config_path = Path(self.path_compared_methods)
        config_data = {
            "methods": [
                {"name": name, "default_path": path}
                for name, path in zip(self.methods, self.default_paths)
            ]
        }
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            raise Exception(f"Failed to save methods config: {str(e)}")

    def get_selected_method(self):
        return self.ui.method_var.get()
    
    def get_color_map(self):
        return self.current_color_map
    
    def update_color_map(self, color_map):
        self.current_color_map = color_map
        
    def load_rgb_image(self, file_path):
        try:
            self.rgb_image = Image.open(file_path)
            return self.rgb_image
        except Exception as e:
            raise Exception(f"Failed to load image sequence: {str(e)}")
    
    def load_method_data(self, method_name, file_path):
        try:
            disp_data = self._load_disparity_data(method_name, file_path)
            
            is_depth_mode = self.ui.vis_mode.get() == "depth"
            
            if is_depth_mode:
                try:
                    vis_img, cbar_img = self._process_depth_data(method_name, disp_data)
                except ValueError as e:
                    self.ui.vis_mode.set("disp")
                    messagebox.showerror("Depth Error", str(e))
                    vis_img, cbar_img = self._process_disparity_data(method_name, disp_data)
            else:
                vis_img, cbar_img = self._process_disparity_data(method_name, disp_data)
                
            return vis_img, cbar_img

        except Exception as e:
            plt.close('all')
            raise ValueError(f"Failed to load {method_name} data: {str(e)}") from e

    def _load_disparity_data(self, method_name, file_path):
        if file_path.endswith('.npy'):
            disp_data = np.load(file_path)
        elif file_path.endswith('.npz'):
            with np.load(file_path) as data:
                disp_data = data['disparity'] if 'disparity' in data else data[list(data.keys())[0]]
        else:
            raise ValueError(f"Unsupported file format '{file_path.split('.')[-1]}' (expected .npy/.npz)")

        if method_name in ["RAFT", "RAFTStereo"]:
            disp_data = -disp_data

        disp_min, disp_max = np.nanmin(disp_data), np.nanmax(disp_data)
        
        if method_name not in self.frame_min_max:
            self.frame_min_max[method_name] = {}
        if self.current_frame not in self.frame_min_max[method_name]:
            self.frame_min_max[method_name][self.current_frame] = {}
        
        self.frame_min_max[method_name][self.current_frame]['min'] = disp_min
        self.frame_min_max[method_name][self.current_frame]['max'] = disp_max
        
        if method_name not in self.default_min_max:
            self.default_min_max[method_name] = {}
        
        self.default_min_max[method_name]['disp_min'] = disp_min
        self.default_min_max[method_name]['disp_max'] = disp_max
        
        clipped_disp = np.where((disp_data >= 0) & (disp_data <= 150), disp_data, np.nan)
        self.method_disp_data[method_name] = clipped_disp
        
        return disp_data

    def _process_depth_data(self, method_name, disp_data):
        data_label = "Depth (m)"
        
        try:
            cx0 = float(self.ui.cx0_var.get())
            cx1 = float(self.ui.cx1_var.get())
            focal = float(self.ui.focal_var.get())
            baseline = float(self.ui.baseline_var.get())
            
            if focal <= 0 or baseline <= 0:
                raise ValueError("Focal length and baseline must be positive values")
                
        except ValueError as e:
            raise ValueError(f"Invalid camera parameters: {str(e)}\n"
                          f"Please enter valid parameters in the Camera Parameters section")
        
        with np.errstate(divide='ignore', invalid='ignore'):
            depth_data = (focal * baseline) / abs(disp_data + (cx1 - cx0))
            depth_data[~np.isfinite(depth_data)] = np.nan
        
        self.method_depth_data[method_name] = depth_data
        depth_min, depth_max = np.nanmin(depth_data), np.nanmax(depth_data)
        
        self.frame_min_max[method_name][self.current_frame]['min'] = depth_min
        self.frame_min_max[method_name][self.current_frame]['max'] = depth_max
        
        if method_name not in self.default_min_max:
            self.default_min_max[method_name] = {}
            
        self.default_min_max[method_name]['depth_min'] = depth_min
        self.default_min_max[method_name]['depth_max'] = depth_max
        
        if self.lock_state[method_name]:
            current_min = self.ui.method_widgets[method_name]['min'].get()
            current_max = self.ui.method_widgets[method_name]['max'].get()
        else:
            wid_min = self.ui.method_widgets[method_name]['min'].get()
            wid_max = self.ui.method_widgets[method_name]['max'].get()
            current_min = wid_min if wid_min != 0 else self.frame_min_max[method_name][self.current_frame]['min']
            current_max = wid_max if wid_max != 0 else self.frame_min_max[method_name][self.current_frame]['max']
            
        return self._create_visualization(depth_data, current_min, current_max, data_label)

    def _process_disparity_data(self, method_name, disp_data):
        data_label = "Disparity (px)"
        
        if self.lock_state[method_name]:
            current_min = self.ui.method_widgets[method_name]['min'].get()
            current_max = self.ui.method_widgets[method_name]['max'].get()
        else:
            wid_min = self.ui.method_widgets[method_name]['min'].get()
            wid_max = self.ui.method_widgets[method_name]['max'].get()
            current_min = wid_min if wid_min != 0 else self.frame_min_max[method_name][self.current_frame]['min']
            current_max = wid_max if wid_max != 0 else self.frame_min_max[method_name][self.current_frame]['max']

        return self._create_visualization(disp_data, current_min, current_max, data_label)

    def _create_visualization(self, data, min_val, max_val, data_label):
        fig_main = plt.figure(figsize=(4, 3), dpi=100) 
        ax_main = fig_main.add_subplot(111) 
        #data[0:1024, 0:1260] = np.nan 
        #data = np.ma.masked_invalid(data)
        data = np.ma.masked_invalid(data)
        cmap = plt.get_cmap(self.ui.color_map_var.get()).copy()
        cmap.set_bad(color='black')
        #cmap.set_bad(color='white')
        #minimum_val = -1 
        #maximum_val = 2 
        #normed = (data - minimum_val) / (maximum_val - minimum_val) 
        #rgba_img = cmap(normed) 
        #rgb_img = (rgba_img[:, :, :3] * 255).astype(np.uint8) 
        #rgb_img[np.isnan(data)] = [0, 0, 0] 
        img = ax_main.imshow(data, vmin=min_val, vmax=max_val, cmap=cmap)
        ax_main.axis('off') 
        buf_vis = io.BytesIO() 
        fig_main.savefig(buf_vis, format='png', bbox_inches='tight', pad_inches=0,  dpi=443.52)
        buf_vis.seek(0) 
        
        vis_img = Image.open(buf_vis)
        #print(np.array(vis_img).shape)
        plt.close(fig_main) 
        
        fig_cbar = plt.figure(figsize=(1, 4), dpi=100) 
        ax_cbar = fig_cbar.add_axes([0.2, 0.05, 0.3, 0.9]) 
        cbar = plt.colorbar(img, cax=ax_cbar) 
        cbar.set_label(data_label, fontsize=8) 
        cbar.ax.tick_params(labelsize=8) 
        buf_cbar = io.BytesIO() 
        fig_cbar.savefig(buf_cbar, format='png', bbox_inches='tight', pad_inches=0.1) 
        buf_cbar.seek(0) 
        cbar_img = Image.open(buf_cbar) 
        plt.close(fig_cbar) 
        return vis_img, cbar_img
        
    def toggle_lock(self, method):
        self.lock_state[method] = not self.lock_state[method]
        reference_method = self.methods[0]
        
        self.lock_state[reference_method] = self.lock_state[self.methods[1]] or self.lock_state[self.methods[2]]

        try:
            sync_min = self.ui.method_widgets[reference_method]['min'].get()
            sync_max = self.ui.method_widgets[reference_method]['max'].get()
            
            if sync_min == 0 and sync_max == 0:
                raise ValueError(f"Reference method '{reference_method}' has min/max values set to 0. "
                            f"Please set valid values before locking.")
            if sync_min >= sync_max:
                raise ValueError(f"Reference method '{reference_method}' has max value <= min value. "
                            f"Max must be greater than min.")
            
            if self.lock_state[method]:
                self.ui.method_widgets[method]['min'].set(sync_min)
                self.ui.method_widgets[method]['max'].set(sync_max)
                        
                if method in self.ui.min_max_entry:
                    if 'min_entry_widget' in self.ui.min_max_entry[method]:
                        self.ui.min_max_entry[method]['min_entry_widget'].config(state='disabled')
                    if 'max_entry_widget' in self.ui.min_max_entry[method]:
                        self.ui.min_max_entry[method]['max_entry_widget'].config(state='disabled')
            else:
                if method in self.ui.min_max_entry:
                    if 'min_entry_widget' in self.ui.min_max_entry[method]:
                        self.ui.min_max_entry[method]['min_entry_widget'].config(state='normal')
                    if 'max_entry_widget' in self.ui.min_max_entry[method]:
                        self.ui.min_max_entry[method]['max_entry_widget'].config(state='normal')
                                
            self.ui.lock_buttons[method].config(
            text="Locked" if self.lock_state[method] else "Unlocked",
            bootstyle="danger" if self.lock_state[method] else "primary"
            )
            self.ui.reset_min_max_buttons[method].config(
                state='disabled' if self.lock_state[method] else 'normal'
            )
            
            status_msg = "Min/Max values synchronized" if self.lock_state[method] else "Min/Max values unlocked"
            self.ui._update_status(status_msg)
            
            self._load_current_frame()
            
        except ValueError as e:
            self.lock_state[method] = not self.lock_state[method]
            messagebox.showerror("Lock Error", str(e))
            self.ui._update_status(f"Error: {str(e)}")
        except Exception as e:
            self.lock_state[method] = not self.lock_state[method]
            messagebox.showerror("Error", f"Failed to toggle lock: {str(e)}")
            self.ui._update_status(f"Error: Failed to toggle lock")

    def reset_min_max(self, method):
        self.is_depth_mode = hasattr(self.ui, 'vis_mode') and self.ui.vis_mode.get() == "depth"
        
        if method in self.default_min_max:
            if self.is_depth_mode:
                min_val = self.default_min_max[method].get('depth_min', 0.0)
                max_val = self.default_min_max[method].get('depth_max', 0.0)
            else:
                min_val = self.default_min_max[method].get('disp_min', 0.0)
                max_val = self.default_min_max[method].get('disp_max', 0.0)
            
            self.ui.min_max_entry[method]['min_entry'].set(round(min_val, 2))
            self.ui.min_max_entry[method]['max_entry'].set(round(max_val, 2))
            
            if method in self.ui.vis_min and method in self.ui.vis_max:
                self.ui.vis_min[method].config(text=f'min = {min_val:.2f}')
                self.ui.vis_max[method].config(text=f'max = {max_val:.2f}')
            
    def _upload_all_files(self, target):
        folder = filedialog.askdirectory()
        if not folder:
            return

        try:
            if target == 'RGB':
                files = sorted(
                    [os.path.join(folder, f) for f in os.listdir(folder) 
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                )
                self._resolve_method_paths(folder)
            else:
                files = sorted(
                    [os.path.join(folder, f) for f in os.listdir(folder) 
                    if f.lower().endswith(('.npy', '.npz'))]
                )
            
            if not files:
                raise ValueError(f"No valid files found for {target}")
                
            self.sorted_files[target] = files
            self.total_frames = len(files)
            self.current_frame = 0
            
            if hasattr(self.ui, 'slider'):
                self.ui.slider.config(to=max(self.total_frames - 1, 0))
                self.ui.slider.set(0)
            
            self._load_current_frame()
            
        except Exception as e:
            self.ui._update_status(f"Error loading {target} files: {str(e)}")
            messagebox.showerror("Upload Error", f"Failed to load {target} files: {str(e)}")
            
    def _resolve_method_paths(self, rgb_folder):
        # Get the parent directory of the RGB folder
        rgb_parent_dir = os.path.dirname(rgb_folder)
        
        for method, default_path in zip(self.methods, self.default_paths):
            if method in self.sorted_files and self.sorted_files[method]:
                continue
                
            potential_paths = []
            path_types = []
            
            # Try to resolve the default path (which might be relative)
            if default_path:
                try:
                    # For relative paths, resolve them relative to the RGB folder
                    if not os.path.isabs(default_path):
                        # Join with RGB folder and normalize
                        resolved_path = os.path.normpath(os.path.join(rgb_folder, default_path))
                    else:
                        # For absolute paths, use as-is
                        resolved_path = default_path
                    
                    if os.path.exists(resolved_path):
                        potential_paths.append(resolved_path)
                        path_types.append("default path")
                except Exception as e:
                    # If there's an error resolving the default path, skip it
                    self.ui._update_status(f"Error resolving default path '{default_path}' for {method}: {str(e)}")
                    messagebox.showerror("Resolving Error", f"Error resolving default path '{default_path}' for {method}: {str(e)}")
                    continue
            
            # Try the sibling directory named after the method
            method_dir = os.path.join(rgb_parent_dir, method)
            try:
                if os.path.exists(method_dir) and method_dir not in potential_paths:
                    potential_paths.append(method_dir)
                    path_types.append("sibling directory")
            except Exception as e:
                self.ui._update_status(f"Error accessing sibling directory '{method_dir}' for {method}: {str(e)}")
                messagebox.showerror("Acesseing Error", f"Error accessing sibling directory '{method_dir}' for {method}: {str(e)}")
                continue
                
            for path, path_type in zip(potential_paths, path_types):
                try:
                    files = sorted(
                        [os.path.join(path, f) for f in os.listdir(path)
                        if f.lower().endswith(('.npy', '.npz'))]
                    )
                    
                    if files:
                        self.sorted_files[method] = files
                        self.ui._update_status(f"Auto-resolved {method} path: {path} ({path_type})")
                        break
                except Exception as e:
                    self.ui._update_status(f"Error accessing files in '{path}' for {method}: {str(e)}")
                    messagebox.showerror("Acesseing Error", f"Error accessing files in '{path}' for {method}: {str(e)}")
                    continue

    def _load_current_frame(self):
        if 'RGB' in self.sorted_files and self.current_frame < len(self.sorted_files['RGB']):
            rgb_path = self.sorted_files['RGB'][self.current_frame]
            try:
                img = self.load_rgb_image(rgb_path)
                self.ui._display_rgb_image(img)
                self.ui.update_frame_index(self.current_frame+1, self.total_frames)
                self.ui._update_status(f"Frame {self.current_frame + 1}/{self.total_frames}")
            except Exception as e:
                self.ui._update_status(f"Error loading image sequence: {str(e)}")

        for method in self.methods:
            if method in self.sorted_files and self.current_frame < len(self.sorted_files[method]):
                data_path = self.sorted_files[method][self.current_frame]
                try:
                    data, cbar = self.load_method_data(method, data_path)
                    self.ui.method_photos_png[method] = data
                    self.ui.method_cbar_png[method] = cbar
                    self.ui.vis_min[method].config(text=f'min = {self.frame_min_max[method][self.current_frame]["min"]:.2f}')
                    self.ui.vis_max[method].config(text=f'max = {self.frame_min_max[method][self.current_frame]["max"]:.2f}')
                    self.ui._display_method_data(method, data, cbar)
                except Exception as e:
                    self.ui._update_status(f"Error loading {method}: {str(e)}")
            else:
                if method in self.ui.method_canvases:
                    self.ui.method_canvases[method].delete("all")
                    self.ui.cbar_canvases[method].delete("all")
                    self.ui.vis_min[method].config(text="")
                    self.ui.vis_max[method].config(text="")
        
    def on_slider_move(self, val):
        frame_idx = int(float(val))
        if frame_idx != self.current_frame:
            self.current_frame = frame_idx
            self._load_current_frame()
    
    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.ui.play_button.config(text="⏸" if self.is_playing else "▶")
        self.set_frame_state_method_params(self.ui.method_params, self.is_playing)
        self.set_frame_state_cam_params(self.ui.cam_params, self.is_playing)
        self.set_frame_state_full_screen(self.is_playing)
        self.set_frame_state(self.ui.methods_frame, self.is_playing)
        self.set_frame_state(self.ui.top_frame, self.is_playing)
        if self.is_playing:
            self._play_loop()
            
    def set_frame_state_full_screen(self, disabled=True):
        for method in self.methods:
            self.ui.fullscreen_buttons[method].config(state="disabled" if disabled else "normal")
    
    def set_frame_state_method_params(self, frame, disabled=True):
        state = 'disabled' if disabled else 'normal'
        if disabled:     
            for child in frame.winfo_children():
                if child.winfo_class() in ('TEntry', 'TCombobox', 'TButton', 'TRadiobutton', 'TCheckbutton'):
                    child.configure(state=state)
                elif child.winfo_class() == 'TLabel':
                    child.configure(foreground='gray' if disabled else 'white')
                elif child.winfo_class() == 'TFrame':
                    self.set_frame_state_method_params(child, disabled)
                    
        else:
            for child in frame.winfo_children():
                if child.winfo_class() in ('TEntry', 'TCombobox', 'TButton', 'TRadiobutton', 'TCheckbutton'):
                    child.configure(state=state)
                elif child.winfo_class() == 'TLabel':
                    child.configure(foreground='gray' if disabled else 'white')
                elif child.winfo_class() == 'TFrame':
                    self.set_frame_state_method_params(child, disabled)
            
            for i, method in enumerate(self.methods):
                if i != 0:
                    if self.lock_state[method]:
                        if method in self.ui.min_max_entry:
                            if 'min_entry_widget' in self.ui.min_max_entry[method]:
                                self.ui.min_max_entry[method]['min_entry_widget'].config(state='disabled')
                            if 'max_entry_widget' in self.ui.min_max_entry[method]:
                                self.ui.min_max_entry[method]['max_entry_widget'].config(state='disabled')
                    else:
                        if method in self.ui.min_max_entry:
                            if 'min_entry_widget' in self.ui.min_max_entry[method]:
                                self.ui.min_max_entry[method]['min_entry_widget'].config(state='normal')
                            if 'max_entry_widget' in self.ui.min_max_entry[method]:
                                self.ui.min_max_entry[method]['max_entry_widget'].config(state='normal')
                                        
                    self.ui.lock_buttons[method].config(
                    text="Locked" if self.lock_state[method] else "Unlocked",
                    bootstyle="danger" if self.lock_state[method] else "primary"
                    )
                    self.ui.reset_min_max_buttons[method].config(
                        state='disabled' if self.lock_state[method] else 'normal'
                    )

    def set_frame_state_cam_params(self, frame, disabled=True):
        state = 'disabled' if disabled else 'normal'
        if disabled:     
            for child in frame.winfo_children():
                if child.winfo_class() in ('TEntry', 'TCombobox', 'TButton', 'TRadiobutton', 'TCheckbutton'):
                    child.configure(state=state)
                elif child.winfo_class() == 'TLabel':
                    child.configure(foreground='gray' if disabled else 'white')
                elif child.winfo_class() == 'TFrame':
                    self.set_frame_state_cam_params(child, disabled)
                    
        else:
            for child in frame.winfo_children():
                if child.winfo_class() in ('TEntry', 'TCombobox', 'TButton', 'TRadiobutton', 'TCheckbutton'):
                    child.configure(state=state)
                elif child.winfo_class() == 'TLabel':
                    child.configure(foreground='gray' if disabled else 'white')
                elif child.winfo_class() == 'TFrame':
                    self.set_frame_state_cam_params(child, disabled)
                    
            self.ui._on_vis_mode_change()
            
    def set_frame_state(self, frame, disabled=True):
        state = 'disabled' if disabled else 'normal'
        for child in frame.winfo_children():
            if child.winfo_class() in ('TEntry', 'TCombobox', 'TButton', 'TRadiobutton', 'TCheckbutton'):
                child.configure(state=state)
            elif child.winfo_class() == 'TLabel':
                child.configure(foreground='gray' if disabled else 'white')
            elif child.winfo_class() == 'TFrame':
                self.set_frame_state(child, disabled)

    def _play_loop(self):
        if not self.is_playing:
            return

        if self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            self.ui.slider.set(self.current_frame)
            self._load_current_frame()
            self.ui.root.after(1, self._play_loop)
        else:
            self.toggle_play()
    
    def reset_app(self):
        try:
            if self.is_playing:
                self.toggle_play()

            for method, window in list(self.ui.fullscreen_windows.items()):
                try:
                    if window.winfo_exists():
                        window.destroy()
                except Exception:
                    continue
            self.ui.fullscreen_windows.clear()

            self.rgb_image = None
            self.method_depth_data.clear()
            self.method_disp_data.clear()
            self.sorted_files.clear()
            self.frame_min_max.clear()

            self._reset_canvas(self.ui.rgb_canvas, is_rgb=True)
            
            for method in self.methods:
                if method in self.ui.method_canvases:
                    self._reset_canvas(self.ui.method_canvases[method])
                if method in self.ui.cbar_canvases:
                    self._reset_canvas(self.ui.cbar_canvases[method])
                
                if method in self.ui.vis_min:
                    self.ui.vis_min[method].config(text="")
                if method in self.ui.vis_max:
                    self.ui.vis_max[method].config(text="")

            self.total_frames = 0
            self.current_frame = 0
            self.ui.slider.set(0)
            self.ui.slider.config(to=0)
            self.ui.frame_index_label.config(text="0/0")
            self.ui.play_button.config(text="▶", bootstyle="primary")
            
            self.ui.method_photos.clear()
            self.ui.method_cbar.clear()
            self.ui.method_photos_png.clear()
            self.ui.method_cbar_png.clear()
            self.ui.rgb_photo = None
            
            gc.collect()
            self.ui.root.update_idletasks()

            self.ui._update_status("Application fully reset")

        except Exception as e:
            messagebox.showerror("Reset Error", f"Failed to reset: {str(e)}")
            self.ui._update_status(f"Reset error: {str(e)}")

    def _reset_canvas(self, canvas, is_rgb=False):
        try:
            blank_img = Image.new('RGB', (1, 1), (255, 255, 255))
            blank_photo = ImageTk.PhotoImage(blank_img)
            
            if is_rgb:
                canvas.delete("all")
                canvas.image = blank_photo
                canvas.create_image(0, 0, image=blank_photo, anchor=ttk.NW)
            else:
                canvas.delete("all")
                canvas.create_image(0, 0, image=blank_photo, anchor=ttk.NW)
                canvas.image = blank_photo
            
            canvas.unbind("<ButtonPress-1>")
            canvas.unbind("<B1-Motion>")
            canvas.unbind("<ButtonRelease-1>")
            canvas.unbind("<MouseWheel>")
            canvas.unbind("<Button-4>")
            canvas.unbind("<Button-5>")
        except Exception:
            pass
        
    def skip_frames(self, nbr_frames):
        self.current_frame += nbr_frames
        
        if self.current_frame < 0:
            self.current_frame = 0
        if self.current_frame >= self.total_frames:
            self.current_frame = self.total_frames-1
            
        self.ui.slider.set(self.current_frame)
        self._load_current_frame()
        
    def _update_visualization(self):
        try:
            self.update_color_map(self.ui.color_map_var.get())

            if self.is_playing:
                self.toggle_play()
                
            current_mode = self.ui.vis_mode.get() == "depth"
                
            self._load_current_frame()
                
            self.ui._update_status("Visualization updated")
            
            with open(self.path_parameters, 'r') as f:
                params = json.load(f)
            
            params["cx0"] = float(self.ui.cx0_var.get())
            params["cx1"] = float(self.ui.cx1_var.get())
            params["color_map"] = self.ui.color_map_var.get()
            params["focal_lenght"] = float(self.ui.focal_var.get())
            params["baseline"] = float(self.ui.baseline_var.get())
            params["is_depth_mode"] = current_mode
            
            for m in self.methods:
                params[m]["min"] = float(self.ui.method_widgets[m]["min"].get())
                params[m]["max"] = float(self.ui.method_widgets[m]["max"].get())
            
            with open(self.path_parameters, 'w') as f:
                json.dump(params, f, indent=4)
                
            self.ui._update_status("Parameters successfully updated in parameters.json")
            
        except Exception as e:
            messagebox.showerror(
                "Update Error", 
                f"Failed to update visualization: {str(e)}"
            )
            self.ui._update_status(f"Error: {str(e)}")
            
    def on_first_method_change(self, method, is_min):
        reference_method = method
        
        try:
            widget_dict = self.ui.method_widgets.get(reference_method)
            if not widget_dict:
                return
                
            var = widget_dict["min"] if is_min else widget_dict["max"]
            
            try:
                val = var.get()
            except Exception:
                return
                
            if val == "" or val is None:
                return
                
            try:
                sync_val = float(val)
            except ValueError:
                return
                
            for i, m in enumerate(self.methods):
                if i != 0 and self.lock_state.get(m, False):
                    target_dict = self.ui.method_widgets.get(m)
                    if target_dict:
                        target_var = target_dict["min"] if is_min else target_dict["max"]
                        try:
                            target_var.set(sync_val)
                        except Exception:
                            continue
        except Exception:
            return