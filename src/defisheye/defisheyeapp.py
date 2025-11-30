#!/usr/bin/env python3.6
# -*- Coding: UTF-8 -*-
"""
Defisheye algorithm.

Developed by: E. S. Pereira.
e-mail: pereira.somoza@gmail.com

Based in the work of F. Weinhaus.
http://www.fmwconcepts.com/imagemagick/defisheye/index.php

Copyright [2019] [E. S. Pereira]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
try:
    # Prefer stdlib importlib.resources when available and complete.
    from importlib import resources
    if not hasattr(resources, "files"):  # Python < 3.9
        raise ImportError
except ImportError:  # pragma: no cover - fallback for older Python versions
    import importlib_resources as resources
import os
import tkinter as tk
import tkinter.ttk as ttk
import pygubu
from tkinter.filedialog import askopenfilename, askdirectory
from tkinter import messagebox
import cv2
from PIL import Image

from .defisheye import Defisheye
import io
import base64


class DefisheyeApp:
    def __init__(self, **kwargs) -> None:
        self.root = tk.Tk()

        self.builder = pygubu.Builder()
        gui_resources = resources.files(__package__).joinpath("gui")
        self._ui = str(gui_resources / "main.ui")

        self.icon = str(gui_resources / "camera.png")

        self.builder.add_from_file(self._ui)
        self.mainwindow = self.builder.get_object("frame1", self.root)

        self.root.title("Defisheye")
        self.root.iconphoto(False, tk.PhotoImage(file=self.icon, master=self.root))

        # Open Image Button
        self._openimageicon = str(gui_resources / "open-image.png")
        self._openimagephoto = tk.PhotoImage(file=self._openimageicon, master=self.root)
        self._open_image_btn = self.builder.get_object("openimage")
        self._open_image_btn['image'] = self._openimagephoto
        self._open_image_btn.configure(command=self.open_image)

        # Edit Image Button
        self._editimageicon = str(gui_resources / "edit-image.png")
        self._editimagephoto = tk.PhotoImage(file=self._editimageicon, master=self.root)
        self._edit_image_btn = self.builder.get_object("editimage")
        self._edit_image_btn['image'] = self._editimagephoto

        self._edit_image_btn.configure(command=self.process_image)

        # Batch Button
        self._batch_btn = self.builder.get_object("batchprocess")
        self._batch_btn.configure(command=self._open_batch_dialog)

        # Image Icon
        self._imageicon = str(gui_resources / "image200x200.png")
        self._imagephoto = tk.PhotoImage(file=self._imageicon, master=self.root)

        # Original Image
        self._original_image_label = self.builder.get_object("originalimage")
        self._original_image_label['image'] = self._imagephoto

        # Edited Image
        self._edited_image_label = self.builder.get_object("editedimage")
        self._edited_image_label['image'] = self._imagephoto

        # Parameters
        self._vars()
        self._fov_entry = self.builder.get_object("entryfov")
        self._fov_entry['textvariable'] = self._fov

        self._fov.set(180)

        self._pfov_entry = self.builder.get_object("entrypfov")
        self._pfov_entry['textvariable'] = self._pfov
        self._pfov.set(120)

        self._xcenter_entry = self.builder.get_object("entryxcenter")
        self._xcenter_entry['textvariable'] = self._xcenter
        self._xcenter.set(-1)

        self._ycenter_entry = self.builder.get_object("entryycenter")
        self._ycenter.set(-1)
        self._ycenter_entry['textvariable'] = self._ycenter

        self._radius_entry = self.builder.get_object("entryradius")
        self._radius.set(-1)
        self._radius_entry['textvariable'] = self._radius

        self._angle_entry = self.builder.get_object("entryangle")
        self._angle.set(-1)
        self._angle_entry['textvariable'] = self._angle

        self._dtype_combo = self.builder.get_object("combodtype")
        self._dtype_combo['values'] = (
            "linear", "equalarea", 'orthographic', "stereographic")
        self._dtype_combo.current(1)
        self._dtype.set(self._dtype_combo['values'][0])
        self._dtype_combo['textvariable'] = self._dtype

        self._format_combo = self.builder.get_object("comboformat")
        self._format_combo['values'] = ('fullframe', 'circular')
        self._format_combo.current(1)
        self._format.set(self._format_combo['values'][0])
        self._format_combo['textvariable'] = self._format

        self._xpand_entry = self.builder.get_object("xentry")
        self._xpand.set(0)
        self._xpand_entry['textvariable'] = self._xpand

    def _current_kwargs(self):
        return {
            "fov": self._fov.get(),
            "pfov": self._pfov.get(),
            "xcenter": self._xcenter.get() if self._xcenter.get() != -1 else None,
            "ycenter": self._ycenter.get() if self._ycenter.get() != -1 else None,
            "radius": self._radius.get() if self._radius.get() != -1 else None,
            "pad": self._xpand.get() if self._xpand.get() > 0 else 0,
            "angle": self._angle.get() if self._angle.get() != -1 else None,
            "dtype": self._dtype.get(),
            "format": self._format.get()
        }

    def _photo_image_from_pil(self, image: Image.Image) -> tk.PhotoImage:
        """Convert a PIL image to a Tk PhotoImage without ImageTk dependency."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return tk.PhotoImage(data=encoded, master=self.root)

    def _vars(self):
        self._fov = tk.IntVar()
        self._pfov = tk.IntVar()
        self._xcenter = tk.IntVar()
        self._ycenter = tk.IntVar()

        self._radius = tk.IntVar()
        self._angle = tk.IntVar()

        self._dtype = tk.StringVar()
        self._format = tk.StringVar()

        self._xpand = tk.IntVar()

        self._original_image = None
        self._original_imag_file = None

        self._processed_image = None

    def open_image(self):
        f_types = [('Jpg Files', '*.jpg'), ('PNG Files', '*.png')]
        self._original_imag_file = askopenfilename(
            multiple=False, filetypes=f_types)

        img = Image.open(self._original_imag_file)

        # width, height = img.size
        width_new = int(400)
        height_new = int(400)
        img_resized = img.resize((width_new, height_new))

        self._original_image = self._photo_image_from_pil(img_resized)
        self._original_image_label['image'] = self._original_image

    def process_image(self):

        vkwargs = self._current_kwargs()

        if self._original_imag_file is not None:
            defisheye = Defisheye(self._original_imag_file, **vkwargs)
            img = defisheye.convert()
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            img = Image.fromarray(img)

            width_new = int(400)
            height_new = int(400)
            img_resized = img.resize((width_new, height_new))

            self._processed_image = self._photo_image_from_pil(img_resized)

            self._edited_image_label['image'] = self._processed_image

    def process_folder(self):
        input_dir = askdirectory(title="Select input images folder", parent=self.root)
        if not input_dir:
            return

        output_dir = askdirectory(title="Select output folder", parent=self.root)
        if not output_dir:
            return
        self._run_batch(input_dir, output_dir)

    def _run_batch(self, input_dir, output_dir):
        os.makedirs(output_dir, exist_ok=True)

        exts = {"png", "jpg", "jpeg"}
        files = [
            fname for fname in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, fname))
            and fname.lower().split(".")[-1] in exts
        ]

        if not files:
            messagebox.showinfo("Defisheye", "No images found in the selected folder.")
            return

        vkwargs = self._current_kwargs()
        for fname in files:
            in_path = os.path.join(input_dir, fname)
            out_path = os.path.join(output_dir, fname)
            obj = Defisheye(in_path, **vkwargs)
            obj.convert(outfile=out_path)

        messagebox.showinfo("Defisheye", f"Processed {len(files)} images into {output_dir}.")

    def _open_batch_dialog(self):
        if hasattr(self, "_batch_window") and self._batch_window.winfo_exists():
            self._batch_window.lift()
            return

        self._batch_window = tk.Toplevel(self.root)
        self._batch_window.title("Batch Process")
        self._batch_window.transient(self.root)
        self._batch_window.resizable(False, False)

        in_var = tk.StringVar()
        out_var = tk.StringVar()
        self._batch_window.columnconfigure(1, weight=1)

        tk.Label(self._batch_window, text="Input folder:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w")
        in_entry = ttk.Entry(self._batch_window, textvariable=in_var, width=40)
        in_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self._batch_window, text="Browse",
                   command=lambda: self._choose_dir(in_var)).grid(
            row=0, column=2, padx=5, pady=5)

        tk.Label(self._batch_window, text="Output folder:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w")
        out_entry = ttk.Entry(self._batch_window, textvariable=out_var, width=40)
        out_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self._batch_window, text="Browse",
                   command=lambda: self._choose_dir(out_var)).grid(
            row=1, column=2, padx=5, pady=5)

        btn_frame = ttk.Frame(self._batch_window)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Cancel",
                   command=self._batch_window.destroy).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Run",
                   command=lambda: self._confirm_batch(in_var.get(), out_var.get())).pack(
            side="left", padx=5)

    def _choose_dir(self, var):
        path = askdirectory(parent=self.root)
        if path:
            var.set(path)

    def _confirm_batch(self, input_dir, output_dir):
        if not input_dir or not output_dir:
            messagebox.showerror("Defisheye", "Please select both input and output folders.")
            return
        if not os.path.isdir(input_dir):
            messagebox.showerror("Defisheye", "Input folder does not exist.")
            return
        try:
            self._run_batch(input_dir, output_dir)
        finally:
            if hasattr(self, "_batch_window") and self._batch_window.winfo_exists():
                self._batch_window.destroy()

    def run(self):
        self.mainwindow.mainloop()
