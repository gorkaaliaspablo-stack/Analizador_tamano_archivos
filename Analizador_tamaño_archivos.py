import os
import sys
import threading
import psutil
from tkinter import ttk, filedialog
import customtkinter as ctk

# Tema base en modo oscuro
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class DirectoryNode:
    """Estructura de datos ligera para el árbol de directorios."""
    def __init__(self, name, path, is_dir=True):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.size = 0
        self.children = []

class WizTreeClone(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PyDiskVisualizer - Analizador de Disco")
        self.geometry("1050x780")
        self.configure(fg_color="#0F172A")  # Fondo oscuro elegante

        self.scanning = False
        self.root_node_data = None
        self.node_map = {}

        # Paleta de colores verde
        self.GREEN_PRIMARY = "#10B981"    # Verde brillante
        self.GREEN_DARK = "#047857"       # Verde oscuro
        self.GREEN_HOVER = "#059669"      # Verde al pasar el mouse
        self.BG_CARD = "#1E293B"          # Fondo de tarjetas
        self.GRAY_BG = "#334155"           # Espacio libre / neutro

        # 1. PANEL SUPERIOR: Selección de disco y botones
        self.top_frame = ctk.CTkFrame(self, fg_color=self.BG_CARD, corner_radius=12)
        self.top_frame.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            self.top_frame, 
            text="💾 Disco:", 
            font=("Segoe UI", 13, "bold"),
            text_color="#F8FAFC"
        ).pack(side="left", padx=(15, 5), pady=12)

        self.drives = self.get_system_drives()
        self.drive_select = ctk.CTkOptionMenu(
            self.top_frame, 
            values=self.drives, 
            command=self.on_drive_changed,
            fg_color=self.GREEN_DARK,
            button_color=self.GREEN_HOVER,
            button_hover_color=self.GREEN_PRIMARY,
            dropdown_fg_color=self.BG_CARD,
            dropdown_hover_color=self.GREEN_DARK,
            text_color="#FFFFFF",
            font=("Segoe UI", 12, "bold")
        )
        self.drive_select.pack(side="left", padx=5, pady=12)

        self.btn_scan = ctk.CTkButton(
            self.top_frame, 
            text="⚡ Escanear Disco", 
            command=self.start_drive_scan,
            fg_color=self.GREEN_PRIMARY,
            hover_color=self.GREEN_HOVER,
            text_color="#000000",
            font=("Segoe UI", 12, "bold"),
            corner_radius=8
        )
        self.btn_scan.pack(side="left", padx=10, pady=12)

        self.btn_folder = ctk.CTkButton(
            self.top_frame, 
            text="📁 Abrir Carpeta...", 
            command=self.select_custom_folder, 
            fg_color="transparent", 
            border_color=self.GREEN_PRIMARY,
            border_width=2,
            text_color=self.GREEN_PRIMARY,
            hover_color="#064E3B",
            font=("Segoe UI", 12, "bold"),
            corner_radius=8
        )
        self.btn_folder.pack(side="left", padx=5, pady=12)

        # 2. PANEL DE INFORMACIÓN Y BARRA DE ALMACENAMIENTO VERDE
        self.disk_info_frame = ctk.CTkFrame(self, fg_color=self.BG_CARD, corner_radius=12)
        self.disk_info_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.lbl_disk_usage = ctk.CTkLabel(
            self.disk_info_frame, 
            text="Cargando métricas de disco...", 
            anchor="w",
            font=("Segoe UI", 12, "bold"),
            text_color="#F1F5F9"
        )
        self.lbl_disk_usage.pack(fill="x", padx=15, pady=(10, 4))

        # Canvas para la barra Verde (Ocupado) / Gris-Verdoso (Libre)
        self.bar_canvas = ctk.CTkCanvas(self.disk_info_frame, height=18, bg=self.GRAY_BG, highlightthickness=0)
        self.bar_canvas.pack(fill="x", padx=15, pady=(2, 12))
        self.bar_canvas.bind("<Configure>", lambda e: self.update_disk_bar())

        # 3. ESTADO Y BARRA DE PROGRESO DE ESCANEO
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=15, pady=(0, 5))

        self.lbl_status = ctk.CTkLabel(
            self.status_frame, 
            text="🟢 Listo para escanear", 
            anchor="w",
            text_color=self.GREEN_PRIMARY,
            font=("Segoe UI", 11, "bold")
        )
        self.lbl_status.pack(fill="x", padx=5)

        self.progress = ctk.CTkProgressBar(
            self, 
            mode="indeterminate", 
            progress_color=self.GREEN_PRIMARY,
            fg_color=self.GRAY_BG
        )
        self.progress.pack(fill="x", padx=15, pady=(0, 10))

        # 4. TABLA ESTILIZADA EN TONOS OSCUROS/VERDES
        self.tree_frame = ctk.CTkFrame(self, fg_color=self.BG_CARD, corner_radius=12)
        self.tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Configurar tema personalizado para ttk.Treeview
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configuración de colores de la tabla
        self.style.configure(
            "Treeview", 
            background="#1E293B",
            foreground="#F8FAFC",
            fieldbackground="#1E293B",
            rowheight=28, 
            font=("Segoe UI" if os.name == "nt" else "Ubuntu", 10)
        )
        self.style.configure(
            "Treeview.Heading", 
            background="#064E3B", 
            foreground="#A7F3D0", 
            font=("Segoe UI" if os.name == "nt" else "Ubuntu", 10, "bold"),
            borderwidth=0
        )
        self.style.map("Treeview", background=[("selected", "#047857")], foreground=[("selected", "#FFFFFF")])

        self.tree = ttk.Treeview(self.tree_frame, columns=("size", "items"), show="tree headings")
        self.tree.heading("#0", text="  Directorios y Archivos", anchor="w")
        self.tree.heading("size", text="Tamaño Total  ", anchor="e")
        self.tree.heading("items", text="Elementos  ", anchor="e")

        self.tree.column("#0", stretch=True, width=620)
        self.tree.column("size", stretch=False, width=150, anchor="e")
        self.tree.column("items", stretch=False, width=110, anchor="e")

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        scrollbar.pack(side="right", fill="y", pady=8)

        self.tree.bind("<<TreeviewOpen>>", self.on_expand_folder)

        # Cargar datos iniciales
        self.current_used_bytes = 0
        self.current_free_bytes = 0
        self.current_total_bytes = 0
        self.on_drive_changed(self.drive_select.get())

    def get_system_drives(self):
        drives = []
        for part in psutil.disk_partitions(all=False):
            if os.path.exists(part.mountpoint):
                drives.append(part.mountpoint)
        return drives if drives else ["/"]

    def format_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def on_drive_changed(self, target_path):
        try:
            usage = psutil.disk_usage(target_path)
            self.current_total_bytes = usage.total
            self.current_used_bytes = usage.used
            self.current_free_bytes = usage.free

            self.lbl_disk_usage.configure(
                text=f"Capacidad Total: {self.format_size(usage.total)}   |   "
                     f"Ocupado: {self.format_size(usage.used)} ({usage.percent}%)   |   "
                     f"Libre: {self.format_size(usage.free)}"
            )
            self.update_disk_bar()
        except Exception as e:
            self.lbl_disk_usage.configure(text=f"No se pudo obtener información del disco: {e}")

    def update_disk_bar(self):
        self.bar_canvas.delete("all")
        width = self.bar_canvas.winfo_width()
        height = self.bar_canvas.winfo_height()

        if width <= 1 or self.current_total_bytes == 0:
            return

        used_ratio = self.current_used_bytes / self.current_total_bytes
        used_width = width * used_ratio

        # Segmento Verde Brillante: Ocupado
        if used_width > 0:
            self.bar_canvas.create_rectangle(0, 0, used_width, height, fill=self.GREEN_PRIMARY, outline="")

        # Segmento Fondo Oscuro: Libre
        if width - used_width > 0:
            self.bar_canvas.create_rectangle(used_width, 0, width, height, fill=self.GRAY_BG, outline="")

    def scan_directory_tree(self, path, root_device=None):
        node = DirectoryNode(os.path.basename(path) or path, path, is_dir=True)
        total_size = 0

        if root_device is None:
            try:
                root_device = os.stat(path).st_dev
            except Exception:
                root_device = None

        SYSTEM_VIRTUAL_DIRS = {'/proc', '/sys', '/dev', '/run', '/snap'}

        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if not self.scanning:
                        return node

                    try:
                        if entry.is_symlink():
                            continue

                        if entry.path in SYSTEM_VIRTUAL_DIRS:
                            continue

                        if root_device is not None:
                            try:
                                entry_stat = entry.stat(follow_symlinks=False)
                                if entry_stat.st_dev != root_device:
                                    continue
                            except Exception:
                                continue
                        else:
                            entry_stat = entry.stat(follow_symlinks=False)

                        if entry.is_file(follow_symlinks=False):
                            file_size = entry_stat.st_size
                            
                            if file_size > 10 * (1024 ** 4):
                                continue

                            child = DirectoryNode(entry.name, entry.path, is_dir=False)
                            child.size = file_size
                            node.children.append(child)
                            total_size += file_size

                        elif entry.is_dir(follow_symlinks=False):
                            child_dir = self.scan_directory_tree(entry.path, root_device)
                            node.children.append(child_dir)
                            total_size += child_dir.size

                    except (PermissionError, FileNotFoundError):
                        continue
                    except Exception:
                        continue

        except (PermissionError, FileNotFoundError):
            pass

        node.size = total_size
        node.children.sort(key=lambda x: x.size, reverse=True)
        return node

    def populate_tree_ui(self, parent_ui_id, data_node):
        for child in data_node.children:
            icon = "📁 " if child.is_dir else "📄 "
            item_count = len(child.children) if child.is_dir else 1
            
            ui_id = self.tree.insert(
                parent_ui_id, 
                "end", 
                text=f"{icon}{child.name}", 
                values=(self.format_size(child.size), f"{item_count} items" if child.is_dir else "-")
            )
            
            self.node_map[ui_id] = child

            if child.is_dir and child.children:
                dummy_id = self.tree.insert(ui_id, "end", text="Cargando...")
                self.node_map[dummy_id] = None

    def on_expand_folder(self, event):
        selected_item = self.tree.focus()
        data_node = self.node_map.get(selected_item)

        if data_node and data_node.is_dir:
            children = self.tree.get_children(selected_item)
            for child in children:
                self.tree.delete(child)

            self.populate_tree_ui(selected_item, data_node)

    def start_drive_scan(self):
        target_path = self.drive_select.get()
        self.run_scan(target_path)

    def select_custom_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.run_scan(folder)

    def run_scan(self, path):
        if self.scanning:
            return

        self.scanning = True
        self.btn_scan.configure(state="disabled")
        self.btn_folder.configure(state="disabled")
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.node_map.clear()

        self.on_drive_changed(path)

        self.progress.start()
        self.lbl_status.configure(text=f"⏳ Escaneando directorio: {path}...", text_color=self.GREEN_PRIMARY)

        def _thread_target():
            self.root_node_data = self.scan_directory_tree(path)
            self.after(0, self._on_scan_finished)

        thread = threading.Thread(target=_thread_target, daemon=True)
        thread.start()

    def _on_scan_finished(self):
        self.progress.stop()
        self.progress.set(1)

        if self.root_node_data:
            root_ui_id = self.tree.insert(
                "", 
                "end", 
                text=f"📁 {self.root_node_data.path}", 
                values=(self.format_size(self.root_node_data.size), f"{len(self.root_node_data.children)} items"),
                open=True
            )
            self.node_map[root_ui_id] = self.root_node_data
            
            self.populate_tree_ui(root_ui_id, self.root_node_data)

            self.lbl_status.configure(
                text=f"✅ Escaneo finalizado. Tamaño total indexado: {self.format_size(self.root_node_data.size)}",
                text_color=self.GREEN_PRIMARY
            )

        self.scanning = False
        self.btn_scan.configure(state="normal")
        self.btn_folder.configure(state="normal")

if __name__ == "__main__":
    app = WizTreeClone()
    app.mainloop()