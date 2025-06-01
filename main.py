import tkinter as tk
from ui.main_window import MainWindow # MainWindow sınıfını import et

if __name__ == "__main__":
    # Python'un modül arama yoluna proje kök dizinini eklemek
    # bazen gerekebilir, özellikle alt paketlerden import yaparken.
    # Ama eğer `m6800_sdk` klasöründen `python main.py` olarak çalıştırırsanız
    # ve `ui` bir paketse (__init__.py içeriyorsa) sorun olmamalı.
    # import sys
    # import os
    # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop() 
