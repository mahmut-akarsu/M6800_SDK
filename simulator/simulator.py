from .cpu import CPU
from .instruction_executor import InstructionExecutor
# opcode_table'ı InstructionExecutor'a vermek için import etmemiz gerekebilir,
# ama InstructionExecutor zaten INSTRUCTION_SET'i doğrudan import ediyor.
# import assembler.opcode_table as ot_module # Eğer InstructionExecutor constructor'ı bekliyorsa

class Simulator:
    def __init__(self):
        self.cpu = CPU()
        # InstructionExecutor, opcode_table modülünü doğrudan import ediyorsa,
        # burada tekrar vermeye gerek yok. Eğer constructor'ı bekliyorsa:
        # self.executor = InstructionExecutor(self.cpu, ot_module)
        self.executor = InstructionExecutor(self.cpu, None) # None geçiyoruz çünkü executor kendi importunu yapıyor
        self.is_running = False # Sürekli çalıştırma için flag
        self.breakpoints = set() # {address1, address2, ...}
        self.max_steps_run = 1000000 # Sürekli çalıştırmada sonsuz döngüleri engellemek için limit

        # UI'ı güncellemek için callback fonksiyonları (opsiyonel, daha sonra eklenebilir)
        self.on_step_callback = None # Her adımdan sonra çağrılır
        self.on_halt_callback = None # CPU durduğunda çağrılır

    def load_program(self, object_code, start_address=0x0000):
        """
        Verilen nesne kodunu CPU belleğine yükler ve PC'yi ayarlar.
        """
        try:
            self.cpu.memory.load_program(object_code, start_address)
            self.cpu.PC = start_address # PC'yi programın başlangıcına ayarla
            self.cpu.is_halted = False # Yeni program yüklenince durma durumunu kaldır
            print(f"Simulator: Program loaded. PC set to ${start_address:04X}.")
            return True
        except ValueError as e:
            print(f"Simulator Error: Could not load program. {e}")
            return False

    def reset_cpu(self, program_start_address=None):
        """CPU'yu sıfırlar ve PC'yi belirtilen adrese (varsa) ayarlar."""
        self.cpu.reset()
        if program_start_address is not None:
            self.cpu.PC = program_start_address
        self.is_running = False
        self.breakpoints.clear()
        if self.on_step_callback: # UI'yı da sıfırlanmış durumla güncelle
            self.on_step_callback(self.cpu.get_state_str(), self.cpu.PC, self.cpu.memory.get_memory_dump(self.cpu.PC, 16))


    def step(self):
        """
        Tek bir CPU komutunu yürütür.
        Döndürülen değer: CPU durmuşsa False, devam ediyorsa True.
        """
        if self.cpu.is_halted:
            print("Simulator: CPU is halted. Cannot step.")
            if self.on_halt_callback:
                self.on_halt_callback("CPU Halted")
            return False

        executed_cycles = self.executor.execute_next_instruction()

        if self.on_step_callback:
            # UI'a güncel durumu gönder
            # Bellek dökümü için PC etrafındaki bir bölgeyi gösterebiliriz
            mem_dump_start = max(0, self.cpu.PC - 8) & 0xFFF0 # 16 byte sınıra hizala
            self.on_step_callback(
                self.cpu.get_state_str(),
                self.cpu.PC, # Bir sonraki PC
                self.cpu.memory.get_memory_dump(mem_dump_start, 32) # Örnek döküm
            )

        if self.cpu.is_halted:
            print(f"Simulator: CPU halted after instruction. Reason may be in executor logs.")
            if self.on_halt_callback:
                self.on_halt_callback(f"CPU Halted at ${self.cpu.PC:04X}")
            return False

        # Breakpoint kontrolü
        if self.cpu.PC in self.breakpoints:
            self.is_running = False # Sürekli çalışıyorsa durdur
            print(f"Simulator: Breakpoint hit at ${self.cpu.PC:04X}.")
            if self.on_halt_callback:
                self.on_halt_callback(f"Breakpoint at ${self.cpu.PC:04X}")
            return False # Breakpoint'te durduğu için False döndür

        return True # Komut yürütüldü, CPU durmadı

    def run(self):
        """
        CPU'yu bir breakpoint'e veya durma durumuna gelene kadar çalıştırır.
        """
        if self.cpu.is_halted:
            print("Simulator: CPU is already halted. Cannot run.")
            if self.on_halt_callback:
                self.on_halt_callback("CPU Halted")
            return

        self.is_running = True
        print("Simulator: Running...")
        steps_taken = 0
        while self.is_running and not self.cpu.is_halted:
            if not self.step(): # step() False dönerse (breakpoint veya halt) döngüden çık
                self.is_running = False # Durumu güncelle
                break
            steps_taken += 1
            if steps_taken >= self.max_steps_run:
                print(f"Simulator: Maximum run steps ({self.max_steps_run}) reached. Halting to prevent infinite loop.")
                self.cpu.is_halted = True # Veya sadece is_running = False
                self.is_running = False
                if self.on_halt_callback:
                    self.on_halt_callback("Max steps reached")
                break
        if not self.is_running and not self.cpu.is_halted:
            # Muhtemelen breakpoint nedeniyle durdu (step() False döndürdü ama cpu.is_halted değil)
            pass
        elif self.cpu.is_halted:
             print("Simulator: Run finished, CPU is halted.")
        else:
             print("Simulator: Run stopped by user or unknown reason.")


    def stop_running(self):
        """Sürekli çalışmayı durdurur."""
        self.is_running = False
        print("Simulator: Run command interrupted.")

    def add_breakpoint(self, address):
        if 0 <= address < self.cpu.memory.size:
            self.breakpoints.add(address)
            print(f"Simulator: Breakpoint added at ${address:04X}.")
        else:
            print(f"Simulator Error: Invalid breakpoint address ${address:04X}.")

    def remove_breakpoint(self, address):
        if address in self.breakpoints:
            self.breakpoints.remove(address)
            print(f"Simulator: Breakpoint removed from ${address:04X}.")
        else:
            print(f"Simulator: No breakpoint at ${address:04X} to remove.")

    def clear_breakpoints(self):
        self.breakpoints.clear()
        print("Simulator: All breakpoints cleared.")

    # --- UI Callback Ayarları ---
    def set_on_step_callback(self, callback_func):
        """Her adımdan sonra çağrılacak UI güncelleme fonksiyonunu ayarlar."""
        self.on_step_callback = callback_func

    def set_on_halt_callback(self, callback_func):
        """CPU durduğunda çağrılacak UI güncelleme fonksiyonunu ayarlar."""
        self.on_halt_callback = callback_func


# Test için örnek kullanım
if __name__ == "__main__":
    sim = Simulator()

    # Basit bir program (LDAA #$10, LDAB #$20, ABA, SWI)
    # Opkodlar: 86 10 C6 20 1B 3F
    test_program = [0x86, 0x10, 0xC6, 0x20, 0x1B, 0x3F]
    program_start_addr = 0x0100

    if sim.load_program(test_program, program_start_addr):
        print("\nInitial CPU State:")
        print(sim.cpu.get_state_str())

        print("\n--- Stepping through program ---")
        # UI callback'lerini simüle edelim
        def ui_update(cpu_state_str, next_pc, mem_dump_str):
            print("\n-- UI Update --")
            print(cpu_state_str)
            print(f"Next PC to execute: ${next_pc:04X}")
            # print(f"Memory near PC: {mem_dump_str}")
            print("----------------")

        def ui_halt(reason):
            print(f"\n!! UI HALT Notification: {reason} !!")

        sim.set_on_step_callback(ui_update)
        sim.set_on_halt_callback(ui_halt)

        # Adım adım çalıştır
        for _ in range(5): # Program 4 komut + SWI
            if not sim.step():
                break
            if sim.cpu.is_halted:
                print("CPU halted during stepping.")
                break

        print("\n--- Resetting and Running with Breakpoint ---")
        sim.reset_cpu(program_start_addr) # PC'yi tekrar başa al
        sim.load_program(test_program, program_start_addr) # Programı tekrar yükle
        sim.add_breakpoint(program_start_addr + 4) # ABA komutunun adresi (0x0104)

        sim.run() # Breakpoint'e kadar çalışmalı

        print("\nCPU State after run (at breakpoint):")
        print(sim.cpu.get_state_str())

        sim.remove_breakpoint(program_start_addr + 4)
        print("\n--- Continuing run after removing breakpoint ---")
        # Breakpoint'ten sonra devam etmek için PC'nin doğru yerde olması lazım.
        # step() zaten breakpoint'te durduğu için, bir sonraki adım normal devam eder.
        # Eğer run() ile durduysa, tekrar run() çağrılabilir.
        # Şu anki PC breakpoint adresi. Bir sonraki step o komutu işler.
        sim.is_running = True # Tekrar çalıştırmak için
        sim.run() # SWI'ye kadar gitmeli

        print("\nFinal CPU State (after SWI):")
        print(sim.cpu.get_state_str()) 
