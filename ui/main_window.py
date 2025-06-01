import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os # Dosya işlemleri için

# Backend sınıflarını import etmemiz gerekiyor.
# Proje kök dizinini Python path'ine eklemek gerekebilir veya göreceli import kullanılabilir.
# Eğer m6800_sdk klasöründen çalıştırıyorsanız:
from assembler.assembler import Assembler
from simulator.simulator import Simulator
# utils.error_handler ileride eklenebilir

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Motorola M6800 SDK - Assembler & Simulator")
        self.root.geometry("1200x800") # Pencere boyutunu ayarla

        # Backend nesneleri
        self.assembler = Assembler()
        self.simulator = Simulator()

        # Dosya yolu için değişken
        self.current_file_path = None

        # Simülatör UI callback'lerini ayarla
        self.simulator.set_on_step_callback(self.update_ui_on_step)
        self.simulator.set_on_halt_callback(self.update_ui_on_halt)

        self._setup_ui() # ÖNCE UI'ı kur, listing_tree oluşturulsun
        self._setup_listing_tree_context_menu() # SONRA context menüyü listing_tree'ye bağla

    def _setup_ui(self):
        # --- Ana Çerçeveler ---
        # Sol taraf: Kod editörü, Nesne kodu, Eşleştirme Tablosu
        # Sağ taraf: Registerlar, Bellek, Kontroller
        main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(main_paned_window, width=700, height=780)
        right_frame = ttk.Frame(main_paned_window, width=480, height=780)
        main_paned_window.add(left_frame, weight=2) # Sol frame daha fazla yer kaplasın
        main_paned_window.add(right_frame, weight=1)

        # --- Sol Taraf UI ---
        self._setup_left_panel(left_frame)

        # --- Sağ Taraf UI ---
        self._setup_right_panel(right_frame)

        # --- Menü Çubuğu ---
        self._setup_menu()

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit menüsü (Kes, Kopyala, Yapıştır vb. eklenebilir)

        build_menu = tk.Menu(menubar, tearoff=0)
        build_menu.add_command(label="Assemble", command=self.assemble_code)
        menubar.add_cascade(label="Build", menu=build_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Load to Simulator", command=self.load_to_simulator)
        run_menu.add_command(label="Run", command=self.run_simulation)
        run_menu.add_command(label="Step", command=self.step_simulation)
        run_menu.add_command(label="Stop", command=self.stop_simulation)
        run_menu.add_command(label="Reset CPU", command=self.reset_simulation)
        run_menu.add_separator()
        run_menu.add_command(label="Add Breakpoint", command=self.add_breakpoint_dialog)
        run_menu.add_command(label="Clear All Breakpoints", command=self.simulator.clear_breakpoints) # Direkt çağrı
        menubar.add_cascade(label="Debug", menu=run_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)


    def _setup_left_panel(self, parent_frame):
        left_paned_window = ttk.PanedWindow(parent_frame, orient=tk.VERTICAL)
        left_paned_window.pack(fill=tk.BOTH, expand=True)

        # Kod Editörü Çerçevesi
        code_editor_frame = ttk.LabelFrame(left_paned_window, text="Assembly Code Editor")
        self.code_editor = scrolledtext.ScrolledText(code_editor_frame, wrap=tk.WORD, width=80, height=20, undo=True)
        self.code_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        left_paned_window.add(code_editor_frame, weight=2) # Daha fazla yer

        # Nesne Kodu ve Listeleme için Notebook (Sekmeli Alan)
        output_notebook = ttk.Notebook(left_paned_window)

        # Nesne Kodu Sekmesi
        object_code_frame = ttk.Frame(output_notebook)
        self.object_code_text = scrolledtext.ScrolledText(object_code_frame, wrap=tk.WORD, width=80, height=10, state=tk.DISABLED)
        self.object_code_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        output_notebook.add(object_code_frame, text="Object Code (Hex)")

        # Assembly-Object Kodu Eşleştirme (Listing) Sekmesi
        listing_frame = ttk.Frame(output_notebook)
        # Treeview for listing
        columns = ("addr", "hex", "source", "comment_error")
        self.listing_tree = ttk.Treeview(listing_frame, columns=columns, show="headings", height=10)
        self.listing_tree.heading("addr", text="Address")
        self.listing_tree.heading("hex", text="Hex Code")
        self.listing_tree.heading("source", text="Source Line")
        self.listing_tree.heading("comment_error", text="Comment/Error")

        self.listing_tree.column("addr", width=70, anchor=tk.W)
        self.listing_tree.column("hex", width=120, anchor=tk.W)
        self.listing_tree.column("source", width=300, anchor=tk.W)
        self.listing_tree.column("comment_error", width=250, anchor=tk.W)

        listing_scrollbar = ttk.Scrollbar(listing_frame, orient="vertical", command=self.listing_tree.yview)
        self.listing_tree.configure(yscrollcommand=listing_scrollbar.set)
        listing_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listing_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        output_notebook.add(listing_frame, text="Listing / Mapping")

        left_paned_window.add(output_notebook, weight=1)


    def _setup_right_panel(self, parent_frame):
        right_main_frame = ttk.Frame(parent_frame)
        right_main_frame.pack(fill=tk.BOTH, expand=True)

        # Kontrol Butonları Çerçevesi
        controls_frame = ttk.LabelFrame(right_main_frame, text="Controls")
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        self.assemble_button = ttk.Button(controls_frame, text="Assemble", command=self.assemble_code)
        self.assemble_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.load_button = ttk.Button(controls_frame, text="Load to Sim", command=self.load_to_simulator, state=tk.DISABLED)
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.run_button = ttk.Button(controls_frame, text="Run", command=self.run_simulation, state=tk.DISABLED)
        self.run_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.step_button = ttk.Button(controls_frame, text="Step", command=self.step_simulation, state=tk.DISABLED)
        self.step_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.stop_button = ttk.Button(controls_frame, text="Stop", command=self.stop_simulation, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.reset_button = ttk.Button(controls_frame, text="Reset CPU", command=self.reset_simulation, state=tk.DISABLED)
        self.reset_button.pack(side=tk.LEFT, padx=5, pady=5)


        # Registerlar Çerçevesi
        registers_frame = ttk.LabelFrame(right_main_frame, text="CPU Registers")
        registers_frame.pack(fill=tk.X, padx=5, pady=(10, 5)) # Üstten 10, alttan 5 padding

        self.reg_labels = {}
        reg_list = ["A", "B", "X", "PC", "SP"]
        for i, reg_name in enumerate(reg_list):
            ttk.Label(registers_frame, text=f"{reg_name}:").grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)
            self.reg_labels[reg_name] = ttk.Label(registers_frame, text="00" if len(reg_name)==1 else "0000", width=6)
            self.reg_labels[reg_name].grid(row=i, column=1, padx=5, pady=2, sticky=tk.W)

        # CCR (Flags)
        ttk.Label(registers_frame, text="CCR:").grid(row=len(reg_list), column=0, padx=5, pady=2, sticky=tk.W)
        self.reg_labels["CCR_STR"] = ttk.Label(registers_frame, text="H:0 I:0 N:0 Z:0 V:0 C:0", width=25)
        self.reg_labels["CCR_STR"].grid(row=len(reg_list), column=1, columnspan=2, padx=5, pady=2, sticky=tk.W)
        ttk.Label(registers_frame, text=" (Hex):").grid(row=len(reg_list), column=3, padx=2, pady=2, sticky=tk.W)
        self.reg_labels["CCR_HEX"] = ttk.Label(registers_frame, text="C0", width=4)
        self.reg_labels["CCR_HEX"].grid(row=len(reg_list), column=4, padx=2, pady=2, sticky=tk.W)


        # Bellek Görünümü Çerçevesi
        memory_frame = ttk.LabelFrame(right_main_frame, text="Memory View")
        memory_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bellek adresi giriş alanı ve git butonu
        mem_goto_frame = ttk.Frame(memory_frame)
        mem_goto_frame.pack(fill=tk.X, pady=2)
        ttk.Label(mem_goto_frame, text="Go to Addr (Hex): $").pack(side=tk.LEFT)
        self.mem_addr_entry = ttk.Entry(mem_goto_frame, width=6)
        self.mem_addr_entry.pack(side=tk.LEFT, padx=2)
        self.mem_addr_entry.insert(0, "0000")
        ttk.Button(mem_goto_frame, text="Go", command=self.update_memory_view_from_entry).pack(side=tk.LEFT, padx=2)

        self.memory_text = scrolledtext.ScrolledText(memory_frame, wrap=tk.WORD, width=50, height=15, state=tk.DISABLED, font=("Courier New", 9))
        self.memory_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Durum Çubuğu (Status Bar) - Hatalar ve mesajlar için
        self.status_bar_text = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_bar_text, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar_text.set("Ready.")

    def show_listing_tree_context_menu(self, event):
        """Sağ tıklama menüsünü gösterir."""
        # Sadece bir satır seçiliyse menüyü göster
        selection = self.listing_tree.selection()
        if selection: # Eğer bir veya daha fazla satır seçiliyse (genellikle tek satır olur)
            # Menüyü event'in olduğu yerde (fare pozisyonunda) göster
            try:
                self.listing_tree_context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                # Menünün doğru şekilde kapanmasını sağla
                self.listing_tree_context_menu.grab_release()
        else: # Hiçbir satır seçili değilse veya sağ tıklama boş bir alana yapıldıysa
            # İsteğe bağlı: Boş alana tıklanınca menü göstermeyebiliriz veya farklı bir menü
            pass

    def _setup_listing_tree_context_menu(self):
        """Listing Tree için sağ tıklama menüsünü ayarlar."""
        self.listing_tree_context_menu = tk.Menu(self.root, tearoff=0)
        self.listing_tree_context_menu.add_command(label="Copy Error/Comment", command=self.copy_listing_error_comment)
        # İleride "Copy Full Line" gibi seçenekler de eklenebilir

        # Sağ tıklama olayını Treeview'a bağla
        self.listing_tree.bind("<Button-3>", self.show_listing_tree_context_menu) # Button-3 genellikle sağ tık
    
    def copy_listing_error_comment(self):
        """Seçili Treeview satırının Comment/Error sütunundaki metni panoya kopyalar."""
        try:
            selected_item_id = self.listing_tree.selection()[0] # Seçili ilk (ve genellikle tek) öğeyi al
            item_values = self.listing_tree.item(selected_item_id, "values")
            # values = (addr, hex_c, src, err_cmt)
            # Son sütun (indeks 3) Comment/Error sütunudur
            if item_values and len(item_values) > 3:
                error_comment_text = item_values[3]
                if error_comment_text:
                    self.root.clipboard_clear()  # Panoyu temizle
                    self.root.clipboard_append(error_comment_text) # Panoya ekle
                    self.status_bar_text.set("Error/Comment copied to clipboard.")
                else:
                    self.status_bar_text.set("No error/comment to copy in selected line.")
            else:
                self.status_bar_text.set("Could not retrieve data from selected line.")
        except IndexError:
            # Hiçbir şey seçili değilse veya beklenmedik bir durum
            self.status_bar_text.set("Please select a line in the listing to copy.")
        except Exception as e:
            self.status_bar_text.set(f"Error copying: {e}")


    # --- Menü Komutları ---
    def new_file(self):
        self.code_editor.delete("1.0", tk.END)
        self.current_file_path = None
        self.status_bar_text.set("New file created.")
        self._clear_outputs()

    def open_file(self):
        filepath = filedialog.askopenfilename(
            defaultextension=".asm",
            filetypes=[("Assembly Files", "*.asm *.s *.txt"), ("All Files", "*.*")]
        )
        if not filepath:
            return
        try:
            with open(filepath, "r") as f:
                self.code_editor.delete("1.0", tk.END)
                self.code_editor.insert("1.0", f.read())
            self.current_file_path = filepath
            self.status_bar_text.set(f"Opened: {os.path.basename(filepath)}")
            self._clear_outputs()
        except Exception as e:
            messagebox.showerror("Error Opening File", str(e))
            self.status_bar_text.set("Error opening file.")

    def save_file(self):
        if not self.current_file_path:
            self.save_as_file()
        else:
            try:
                with open(self.current_file_path, "w") as f:
                    f.write(self.code_editor.get("1.0", tk.END).strip())
                self.status_bar_text.set(f"Saved: {os.path.basename(self.current_file_path)}")
            except Exception as e:
                messagebox.showerror("Error Saving File", str(e))
                self.status_bar_text.set("Error saving file.")

    def save_as_file(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".asm",
            filetypes=[("Assembly Files", "*.asm *.s"), ("All Files", "*.*")]
        )
        if not filepath:
            return
        self.current_file_path = filepath
        self.save_file()

    def show_about(self):
        messagebox.showinfo("About M6800 SDK", "Motorola M6800 Assembler & Simulator\n\nDeveloped using Python and Tkinter.")

    def _clear_outputs(self):
        self.object_code_text.config(state=tk.NORMAL)
        self.object_code_text.delete("1.0", tk.END)
        self.object_code_text.config(state=tk.DISABLED)
        for item in self.listing_tree.get_children():
            self.listing_tree.delete(item)
        self.load_button.config(state=tk.DISABLED)
        self.run_button.config(state=tk.DISABLED)
        self.step_button.config(state=tk.DISABLED)
        self.reset_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)


    # --- Assembler ve Simülatör Komutları ---
    def assemble_code(self): # Bu metodu biraz güncelleyelim
        self._clear_outputs()
        self.status_bar_text.set("Assembling...")
        self.root.update_idletasks()

        source_code = self.code_editor.get("1.0", tk.END)
        success, object_code, listing, errors = self.assembler.assemble(source_code)

        # Listing'i göster (hatalı veya başarılı olsun)
        for item in self.listing_tree.get_children(): # Önceki listing'i temizle
            self.listing_tree.delete(item)

        for item_data in listing: # assembler.py'den gelen listing'i kullan
            addr, hex_c, src, err_cmt = item_data
            tags_tuple = () # tag'leri tuple olarak tanımla
            # err_cmt'nin string olduğundan emin ol, bazen None gelebilir
            err_cmt_str = str(err_cmt if err_cmt is not None else "")

            if "ERROR" in err_cmt_str.upper() or "ERR" in hex_c.upper() or (not success and not err_cmt_str):
                tags_tuple = ('error_line',) # tag'i tuple olarak ata

            self.listing_tree.insert("", tk.END, values=(addr, hex_c, src.strip(), err_cmt_str), tags=tags_tuple)

        self.listing_tree.tag_configure('error_line', background='pink', foreground='red') # Hata satırlarını renklendir

        if success:
            self.status_bar_text.set("Assembly successful.")
            self.object_code_text.config(state=tk.NORMAL)
            obj_code_hex = " ".join([f"{b:02X}" for b in object_code])
            self.object_code_text.insert("1.0", obj_code_hex)
            self.object_code_text.config(state=tk.DISABLED)
            self.load_button.config(state=tk.NORMAL)
        else:
            error_count = len(errors)
            self.status_bar_text.set(f"Assembly failed with {error_count} error(s). See listing.")
            # Hatalar listing'de zaten gösteriliyor. İlk hatayı messagebox'ta göstermek opsiyonel.
            if errors:
                first_error_detail = errors[0] # assembler.py'den gelen formatı kontrol et
                # Hata mesajı formatı: "Error (L:line_num): message -> 'original_line'"
                messagebox.showerror("Assembly Error", f"Assembly failed. See listing for details.\nFirst detected error: {first_error_detail}")

    def load_to_simulator(self):
        if not self.assembler.object_code:
            messagebox.showwarning("Load Error", "No object code to load. Please assemble first.")
            return

        # Programın başlangıç adresini al (genellikle ORG ile belirlenir)
        start_address = self.assembler.program_origin
        if self.simulator.load_program(self.assembler.object_code, start_address):
            self.status_bar_text.set(f"Program loaded. PC: ${start_address:04X}")
            self.run_button.config(state=tk.NORMAL)
            self.step_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED) # Stop butonu run sırasında aktif olmalı
            self.update_ui_on_step(self.simulator.cpu.get_state_str(), self.simulator.cpu.PC,
                                   self.simulator.cpu.memory.get_memory_dump(self.simulator.cpu.PC, 32))
        else:
            messagebox.showerror("Load Error", "Failed to load program into simulator memory.")
            self.status_bar_text.set("Error loading program to simulator.")


    def run_simulation(self):
        self.status_bar_text.set("Running simulation...")
        self.run_button.config(state=tk.DISABLED)
        self.step_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.simulator.run() # Bu bloklayıcı olabilir, thread kullanmak gerekebilir
        # run() bittiğinde (breakpoint, halt, max_steps) UI güncellenmeli.
        # on_halt_callback bunu yapacak.
        # Eğer run bittiyse (halt değilse, yani breakpoint veya stop ile) butonları tekrar ayarla
        if not self.simulator.cpu.is_halted:
            self.run_button.config(state=tk.NORMAL)
            self.step_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)


    def step_simulation(self):
        self.status_bar_text.set("Stepping...")
        self.simulator.step()
        # update_ui_on_step callback'i UI'ı güncelleyecek.
        # Eğer step sonrası durduysa, butonları ayarla
        if self.simulator.cpu.is_halted:
            self.run_button.config(state=tk.DISABLED)
            self.step_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)
        else: # Durmadıysa, butonlar hala aktif
            self.run_button.config(state=tk.NORMAL)
            self.step_button.config(state=tk.NORMAL)


    def stop_simulation(self):
        self.simulator.stop_running()
        self.status_bar_text.set("Simulation stopped by user.")
        self.run_button.config(state=tk.NORMAL)
        self.step_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def reset_simulation(self):
        # Simülatör resetlendiğinde programın başlangıç adresini bilmemiz lazım.
        # Assembler'dan alabiliriz.
        start_addr = self.assembler.program_origin if self.assembler.object_code else 0
        self.simulator.reset_cpu(start_addr)
        self.status_bar_text.set("CPU Reset. Load program to run.")
        self.run_button.config(state=tk.DISABLED)
        self.step_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        # UI'ı resetlenmiş CPU durumuyla güncelle
        self.update_ui_on_step(self.simulator.cpu.get_state_str(), self.simulator.cpu.PC,
                               self.simulator.cpu.memory.get_memory_dump(self.simulator.cpu.PC, 32))


    def add_breakpoint_dialog(self):
        addr_str = tk.simpledialog.askstring("Add Breakpoint", "Enter address (hex, e.g., 0100 or $100):")
        if addr_str:
            try:
                if addr_str.startswith('$'): addr_str = addr_str[1:]
                addr = int(addr_str, 16)
                self.simulator.add_breakpoint(addr)
                self.status_bar_text.set(f"Breakpoint added at ${addr:04X}")
            except ValueError:
                messagebox.showerror("Invalid Address", "Please enter a valid hexadecimal address.")

    # --- UI Güncelleme Callback'leri ---
    def update_ui_on_step(self, cpu_state_str, next_pc, memory_dump_str):
        """Simülatörden gelen bilgilerle UI'ı günceller."""
        # Registerları güncelle
        # cpu_state_str'ı parse etmek yerine direkt CPU nesnesinden alalım
        self.reg_labels["A"].config(text=f"{self.simulator.cpu.A:02X}")
        self.reg_labels["B"].config(text=f"{self.simulator.cpu.B:02X}")
        self.reg_labels["X"].config(text=f"{self.simulator.cpu.X:04X}")
        self.reg_labels["PC"].config(text=f"{self.simulator.cpu.PC:04X}") # Bu bir sonraki PC
        self.reg_labels["SP"].config(text=f"{self.simulator.cpu.SP:04X}")
        self.reg_labels["CCR_STR"].config(text=str(self.simulator.cpu.CCR))
        self.reg_labels["CCR_HEX"].config(text=f"{self.simulator.cpu.CCR.get_byte():02X}")

        # Bellek görünümünü güncelle
        self.update_memory_view(self.simulator.cpu.PC) # PC etrafını göster

        # Listing'de bir sonraki çalışacak satırı vurgula (opsiyonel, daha karmaşık)
        # self.highlight_listing_line(next_pc)

        self.root.update_idletasks()

    def update_ui_on_halt(self, reason):
        """CPU durduğunda UI'ı günceller."""
        self.status_bar_text.set(f"HALTED: {reason}")
        self.run_button.config(state=tk.DISABLED)
        self.step_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        # Diğer UI güncellemeleri (örn: registerların son hali zaten on_step ile güncellenmiş olabilir)
        messagebox.showinfo("Simulation Halted", reason)


    def update_memory_view(self, center_address, num_lines=16, bytes_per_line=16):
        """Bellek görünümünü günceller."""
        self.memory_text.config(state=tk.NORMAL)
        self.memory_text.delete("1.0", tk.END)

        # Gösterilecek başlangıç adresini 16 byte'lık sınıra hizala
        start_addr_display = max(0, center_address - (num_lines // 2 * bytes_per_line))
        start_addr_display &= ~(bytes_per_line - 1) # 0xFFF0 gibi

        output_lines = []
        for i in range(num_lines):
            current_addr_line_start = start_addr_display + (i * bytes_per_line)
            if current_addr_line_start >= self.simulator.cpu.memory.size:
                break

            hex_bytes = []
            ascii_chars = []
            for j in range(bytes_per_line):
                addr_to_read = current_addr_line_start + j
                if addr_to_read < self.simulator.cpu.memory.size:
                    byte_val = self.simulator.cpu.memory.read_byte(addr_to_read)
                    hex_bytes.append(f"{byte_val:02X}")
                    # Yazdırılabilir ASCII karakterleri
                    ascii_chars.append(chr(byte_val) if 32 <= byte_val <= 126 else '.')
                else:
                    hex_bytes.append("  ") # Bellek sonunu geçti
                    ascii_chars.append(" ")

            line_str = f"${current_addr_line_start:04X}: {' '.join(hex_bytes)}  |{''.join(ascii_chars)}|"
            output_lines.append(line_str)

        self.memory_text.insert("1.0", "\n".join(output_lines))
        self.memory_text.config(state=tk.DISABLED)

    def update_memory_view_from_entry(self):
        try:
            addr_str = self.mem_addr_entry.get()
            if addr_str.startswith('$'): addr_str = addr_str[1:]
            addr = int(addr_str, 16)
            self.update_memory_view(addr)
        except ValueError:
            messagebox.showerror("Invalid Address", "Please enter a valid hexadecimal address for memory view.")
 
