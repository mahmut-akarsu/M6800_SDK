from assembler.opcode_table import FLAG_H, FLAG_I, FLAG_N, FLAG_Z, FLAG_V, FLAG_C

class Memory:
    def __init__(self, size=65536): # M6800 16-bit adres alanı (64KB)
        self.size = size
        self.memory_array = bytearray(size) # Belleği bytearray olarak tutalım

    def read_byte(self, address):
        if 0 <= address < self.size:
            return self.memory_array[address]
        else:
            # Hata yönetimi: Geçersiz adres
            # print(f"Memory Read Error: Address {address:04X} out of bounds.")
            raise ValueError(f"Memory Read Error: Address {address:04X} out of bounds (0000-{self.size-1:04X}).")

    def write_byte(self, address, value):
        if not (0 <= value <= 255):
            raise ValueError(f"Memory Write Error: Value {value} is not a valid byte.")
        if 0 <= address < self.size:
            self.memory_array[address] = value
        else:
            # Hata yönetimi: Geçersiz adres
            # print(f"Memory Write Error: Address {address:04X} out of bounds.")
            raise ValueError(f"Memory Write Error: Address {address:04X} out of bounds (0000-{self.size-1:04X}).")

    def read_word(self, address):
        """Bellekten ardışık iki byte (word) okur (Big-Endian)."""
        high_byte = self.read_byte(address)
        low_byte = self.read_byte(address + 1) # Bir sonraki adresten düşük byte'ı oku
        return (high_byte << 8) | low_byte

    def write_word(self, address, value):
        """Belleğe ardışık iki byte (word) yazar (Big-Endian)."""
        if not (0 <= value <= 65535):
            raise ValueError(f"Memory Write Error: Value {value} is not a valid word.")
        high_byte = (value >> 8) & 0xFF
        low_byte = value & 0xFF
        self.write_byte(address, high_byte)
        self.write_byte(address + 1, low_byte)

    def load_program(self, object_code, start_address):
        """Verilen nesne kodunu bellekte belirtilen adresten itibaren yükler."""
        if not (0 <= start_address < self.size):
            raise ValueError(f"Load Program Error: Start address {start_address:04X} out of bounds.")
        if start_address + len(object_code) > self.size:
            raise ValueError("Load Program Error: Program too large for memory.")

        for i, byte_val in enumerate(object_code):
            self.memory_array[start_address + i] = byte_val
        print(f"Program loaded into memory starting at ${start_address:04X}, size: {len(object_code)} bytes.")

    def get_memory_dump(self, start_address, num_bytes):
        """Belleğin belirli bir bölümünü string olarak döndürür (hex formatında)."""
        if not (0 <= start_address < self.size and start_address + num_bytes <= self.size):
            return "Invalid memory range for dump."
        dump = []
        for i in range(num_bytes):
            dump.append(f"{self.memory_array[start_address + i]:02X}")
        return " ".join(dump)

    def clear(self):
        """Belleği sıfırlar."""
        self.memory_array = bytearray(self.size)


class CCR: # Condition Code Register
    def __init__(self):
        # H I N Z V C (Bit 5 den 0 a)
        # Örnek: CCR byte'ı -> 0bHINZVC00 (M6800'de CCR 6 bit, ilk 2 bit kullanılmaz veya özel)
        # Motorola dokümanlarında genellikle HINZVC olarak gösterilir.
        # Biz de bu 6 flag'i ayrı ayrı boolean olarak tutalım.
        self.H = False # Bit 5 - Half Carry
        self.I = False # Bit 4 - Interrupt Mask (Başlangıçta False (kesmeler etkin) veya True olabilir)
        self.N = False # Bit 3 - Negative
        self.Z = False # Bit 2 - Zero
        self.V = False # Bit 1 - Overflow
        self.C = False # Bit 0 - Carry/Borrow

    def get_byte(self):
        """CCR flag'lerini tek bir byte olarak döndürür."""
        # M6800'de CCR'nin ilk iki biti (bit 7 ve 6) her zaman 1'dir.
        byte_val = 0b11000000
        if self.H: byte_val |= (1 << 5)
        if self.I: byte_val |= (1 << 4)
        if self.N: byte_val |= (1 << 3)
        if self.Z: byte_val |= (1 << 2)
        if self.V: byte_val |= (1 << 1)
        if self.C: byte_val |= (1 << 0)
        return byte_val

    def set_from_byte(self, byte_val):
        """Verilen byte değerine göre CCR flag'lerini ayarlar."""
        self.H = bool(byte_val & (1 << 5))
        self.I = bool(byte_val & (1 << 4))
        self.N = bool(byte_val & (1 << 3))
        self.Z = bool(byte_val & (1 << 2))
        self.V = bool(byte_val & (1 << 1))
        self.C = bool(byte_val & (1 << 0))

    def __str__(self):
        return (f"H:{int(self.H)} I:{int(self.I)} N:{int(self.N)} "
                f"Z:{int(self.Z)} V:{int(self.V)} C:{int(self.C)}")

class CPU:
    def __init__(self):
        self.A = 0  # Akümülatör A (8-bit)
        self.B = 0  # Akümülatör B (8-bit)
        self.X = 0  # Index Register (16-bit)
        self.PC = 0 # Program Counter (16-bit)
        self.SP = 0 # Stack Pointer (16-bit) - Genellikle RAM'in sonundan başlar
        self.CCR = CCR() # Condition Code Register
        self.memory = Memory() # 64KB Bellek

        self.is_halted = False # SWI, WAI veya tanımsız komut sonrası durma durumu
        self.cycles_executed = 0 # Toplam yürütülen döngü sayısı (opsiyonel)

    def reset(self):
        """CPU'yu başlangıç durumuna sıfırlar."""
        self.A = 0
        self.B = 0
        self.X = 0
        # PC normalde reset vektöründen ($FFFE-$FFFF) yüklenir.
        # Simülatör için programın başlangıç adresine set edilebilir.
        self.PC = 0 # Veya programın yüklendiği adres
        # SP de genellikle RAM'in sonuna yakın bir yerden başlar.
        # Örnek: $A000 (M6800 sistemlerinde RAM genellikle $0000-$A000 arasındadır)
        # Simülatörde kullanıcı tarafından ayarlanabilir veya varsayılan bir değer.
        self.SP = 0x01FF # Örnek bir stack başlangıç adresi (sayfa 1'in sonu)
        self.CCR = CCR() # Flag'leri sıfırla (I flag'i hariç, o donanıma bağlı)
        self.memory.clear() # Belleği temizle
        self.is_halted = False
        self.cycles_executed = 0
        print("CPU Reset.")

    def get_state_str(self):
        """CPU'nun mevcut durumunu string olarak döndürür."""
        return (f"A: {self.A:02X}  B: {self.B:02X}  X: {self.X:04X}\n"
                f"PC: {self.PC:04X} SP: {self.SP:04X} CCR: {self.CCR} ({self.CCR.get_byte():02X})")

    # Yardımcı metodlar (flag ayarları için)
    def set_nz_flags(self, result_8bit):
        """8-bit sonuca göre N ve Z flag'lerini ayarlar."""
        result_8bit &= 0xFF # Sadece 8 bit olduğundan emin ol
        self.CCR.N = bool(result_8bit & 0x80) # En anlamlı bit 1 ise Negatif
        self.CCR.Z = (result_8bit == 0)

    def set_nz_flags_16bit(self, result_16bit):
        """16-bit sonuca göre N ve Z flag'lerini ayarlar."""
        result_16bit &= 0xFFFF
        self.CCR.N = bool(result_16bit & 0x8000)
        self.CCR.Z = (result_16bit == 0)

    # Yığın işlemleri
    def push_byte_to_stack(self, value):
        self.memory.write_byte(self.SP, value & 0xFF)
        self.SP = (self.SP - 1) & 0xFFFF # SP'yi azalt (stack aşağı doğru büyür)

    def pop_byte_from_stack(self):
        self.SP = (self.SP + 1) & 0xFFFF # SP'yi artır
        return self.memory.read_byte(self.SP)

    def push_word_to_stack(self, value):
        # Önce düşük byte, sonra yüksek byte (M6800 stack'i böyle çalışır)
        self.push_byte_to_stack(value & 0xFF)       # Low byte
        self.push_byte_to_stack((value >> 8) & 0xFF) # High byte

    def pop_word_from_stack(self):
        high_byte = self.pop_byte_from_stack()
        low_byte = self.pop_byte_from_stack()
        return (high_byte << 8) | low_byte

# Test için örnek kullanım
if __name__ == "__main__":
    cpu = CPU()
    cpu.reset()
    print(cpu.get_state_str())

    cpu.memory.write_byte(0x0000, 0xAA)
    cpu.memory.write_byte(0x0001, 0xBB)
    print(f"Memory @0000: {cpu.memory.read_byte(0x0000):02X}")
    print(f"Memory Word @0000: {cpu.memory.read_word(0x0000):04X}") # AA BB okumalı

    cpu.A = 0x80
    cpu.set_nz_flags(cpu.A)
    print(f"After A=0x80, CCR: {cpu.CCR}") # N=1, Z=0 olmalı

    cpu.A = 0x00
    cpu.set_nz_flags(cpu.A)
    print(f"After A=0x00, CCR: {cpu.CCR}") # N=0, Z=1 olmalı

    print(f"Initial SP: {cpu.SP:04X}")
    cpu.push_word_to_stack(0x1234) # Stack'e 34 sonra 12 yazılmalı
    print(f"SP after push word: {cpu.SP:04X}") # SP 2 azalmalı
    # Stack'teki değerler: SP+1 -> 12 (high), SP+2 -> 34 (low)
    print(f"Mem @ {cpu.SP+1:04X}: {cpu.memory.read_byte(cpu.SP+1):02X}")
    print(f"Mem @ {cpu.SP+2:04X}: {cpu.memory.read_byte(cpu.SP+2):02X}")

    popped_val = cpu.pop_word_from_stack()
    print(f"Popped Word: {popped_val:04X}") # 0x1234 olmalı
    print(f"SP after pop word: {cpu.SP:04X}") # Orijinal SP'ye dönmeli (ya da push öncesi SP'ye) 
