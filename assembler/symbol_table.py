class SymbolTable:
    def __init__(self):
        self._symbols = {}  # Sembol adı -> adres eşlemesi

    def add_symbol(self, name, address):
        """Sembol tablosuna yeni bir sembol ekler."""
        name = name.upper() # Sembol adlarını büyük harfe çevirerek case-insensitivity sağlayabiliriz
        if name in self._symbols:
            # Normalde bu bir hata durumudur (redefinition), ama bazı assembler'lar
            # son tanımı kabul edebilir. Şimdilik üzerine yazıyoruz veya hata verebiliriz.
            # print(f"Warning: Symbol '{name}' redefined.") # Ya da hata fırlat
            pass # Ya da hata yönetimi eklenir
        self._symbols[name] = address

    def get_address(self, name):
        """Verilen sembol adının adresini döndürür."""
        name = name.upper()
        return self._symbols.get(name) # None döner eğer sembol yoksa

    def has_symbol(self, name):
        """Verilen sembolün tabloda olup olmadığını kontrol eder."""
        name = name.upper()
        return name in self._symbols

    def get_all_symbols(self):
        """Tüm sembolleri ve adreslerini bir sözlük olarak döndürür."""
        return self._symbols.copy()

    def clear(self):
        """Sembol tablosunu temizler."""
        self._symbols.clear()

    def __str__(self):
        return f"SymbolTable({self._symbols})"

# Test için örnek kullanım
if __name__ == "__main__":
    st = SymbolTable()
    st.add_symbol("LOOP", 0x0100)
    st.add_symbol("DATA", 0x02A0)
    print(st.get_address("LOOP"))
    print(st.get_address("UNKNOWN"))
    print(st.has_symbol("DATA"))
    print(st) 
