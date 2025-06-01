# m6800_sdk/assembler/code_generator.py

from .symbol_table import SymbolTable
# opcode_table'dan mod sabitlerini ve diğer bilgileri alacağız
from .opcode_table import MODE_IMPLIED, MODE_IMMEDIATE, MODE_DIRECT, MODE_EXTENDED, MODE_INDEXED, MODE_RELATIVE

class CodeGenerator:
    def __init__(self, symbol_table: SymbolTable, opcode_table_module):
        self.symbol_table = symbol_table
        self.opcode_table = opcode_table_module # opcode_table.py modülünün kendisi
        self.errors = [] # Kod üretimi sırasında oluşabilecek hatalar

    def _add_error(self, line_number, message, original_line=""):
        # Bu hatalar Assembler sınıfına iletilmeli veya burada toplanıp sonra alınmalı.
        # Şimdilik kendi listesinde tutalım.
        self.errors.append(f"CodeGen Error (L:{line_number}): {message} -> '{original_line}'")

    def generate_code_for_instruction(self, parsed_instruction):
        """
        Verilen ParsedInstruction için makine kodu byte'larını üretir.
        Döndürülen değer: (list_of_bytes, error_message_or_none)
        """
        self.errors = [] # Her çağrıda hataları sıfırla
        pi = parsed_instruction
        generated_bytes = []

        if pi.error and not pi.is_directive: # Syntax analizinden gelen hata varsa ve direktif değilse
            # Direktif hataları zaten syntax analyzer tarafından işaretlenmiş olabilir,
            # ama direktifler için kod üretmeye çalışabiliriz (örn: FCB'deki hatalı değer).
            # Şimdilik komut hatalarında direkt boş dönelim.
            # self._add_error(pi.token.line_number, f"Syntax error prevents code generation: {pi.error}", pi.token.original_line)
            return [], f"Syntax error prevents code generation: {pi.error}" # Hata mesajını da döndür

        if pi.is_directive:
            directive_name = pi.mnemonic.upper()
            if directive_name == 'FCB':
                for val_op in pi.operands: # pi.operands artık çözümlenmiş değerler listesi
                    try:
                        # Syntax analyzer'dan gelen değerin uygun türde olması beklenir (int)
                        # Ama yine de kontrol edelim.
                        byte_val = 0
                        if isinstance(val_op, str): # Etiket veya $XX, %BB gibi olabilir
                            if val_op.startswith('$'): byte_val = int(val_op[1:], 16)
                            elif val_op.startswith('%'): byte_val = int(val_op[1:], 2)
                            elif val_op.startswith("'") and val_op.endswith("'") and len(val_op) == 3: byte_val = ord(val_op[1])
                            else: # Decimal veya çözümlenmemiş etiket
                                sym_addr = self.symbol_table.get_address(val_op)
                                if sym_addr is not None:
                                    byte_val = sym_addr
                                else:
                                    byte_val = int(val_op) # Decimal dene
                        else: # Zaten int ise
                            byte_val = int(val_op)

                        if not (0 <= byte_val <= 255):
                            raise ValueError("Byte value out of range")
                        generated_bytes.append(byte_val)
                    except ValueError as e:
                        err_msg = f"Invalid byte value for FCB '{val_op}': {e}"
                        self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                        return [], err_msg
            elif directive_name == 'FDB':
                for val_op in pi.operands:
                    try:
                        word_val = 0
                        if isinstance(val_op, str): # Etiket veya $XXXX gibi olabilir
                            if val_op.startswith('$'): word_val = int(val_op[1:], 16)
                            else: # Decimal veya çözümlenmemiş etiket
                                sym_addr = self.symbol_table.get_address(val_op)
                                if sym_addr is not None:
                                    word_val = sym_addr
                                else:
                                    word_val = int(val_op)
                        else: # Zaten int ise
                            word_val = int(val_op)

                        if not (0 <= word_val <= 65535):
                            raise ValueError("Word value out of range")
                        generated_bytes.append((word_val >> 8) & 0xFF) # High byte
                        generated_bytes.append(word_val & 0xFF)        # Low byte
                    except ValueError as e:
                        err_msg = f"Invalid word value for FDB '{val_op}': {e}"
                        self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                        return [], err_msg
            # ORG, EQU, RMB, END direktifleri doğrudan byte üretmez, Assembler sınıfı tarafından yönetilir.
            # Bu yüzden burada onlar için özel bir işlem yok.
            return generated_bytes, None

        # M6800 Komutu ise
        if not pi.mnemonic or not pi.op_info:
            # Bu durum normalde olmamalı, syntax analyzer yakalamış olmalı
            err_msg = "Missing mnemonic or op_info for code generation."
            self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
            return [], err_msg

        opcode = pi.op_info.get('opcode')
        num_bytes_expected = pi.op_info.get('bytes') # opcode_table'dan beklenen byte sayısı
        addressing_mode = pi.addressing_mode
        operand_value_from_parser = pi.operands[0] if pi.operands else None # Syntax analizinden gelen operand

        if opcode is None:
            err_msg = f"Opcode not found for '{pi.mnemonic}' in mode '{addressing_mode}'."
            self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
            return [], err_msg

        generated_bytes.append(opcode)
        actual_operand_byte_count = 0

        if addressing_mode == MODE_IMMEDIATE:
            if not isinstance(operand_value_from_parser, int) or not (0 <= operand_value_from_parser <= 0xFF) :
                err_msg = f"Invalid immediate value for '{pi.mnemonic}': {operand_value_from_parser}. Expected 8-bit int."
                self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                return [], err_msg
            generated_bytes.append(operand_value_from_parser & 0xFF)
            actual_operand_byte_count = 1
        elif addressing_mode == MODE_DIRECT:
            target_address = operand_value_from_parser
            if isinstance(operand_value_from_parser, str): # Etiket
                addr = self.symbol_table.get_address(operand_value_from_parser)
                if addr is None:
                    err_msg = f"Undefined symbol '{operand_value_from_parser}' for DIRECT mode."
                    self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                    return [], err_msg
                target_address = addr
            if not isinstance(target_address, int) or not (0 <= target_address <= 0xFF):
                err_msg = f"Address '{target_address:X}' out of range for DIRECT mode (00-FF)."
                self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                return [], err_msg
            generated_bytes.append(target_address & 0xFF)
            actual_operand_byte_count = 1
        elif addressing_mode == MODE_EXTENDED:
            target_address = operand_value_from_parser
            if isinstance(operand_value_from_parser, str): # Etiket
                addr = self.symbol_table.get_address(operand_value_from_parser)
                if addr is None:
                    err_msg = f"Undefined symbol '{operand_value_from_parser}' for EXTENDED mode."
                    self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                    return [], err_msg
                target_address = addr
            if not isinstance(target_address, int) or not (0 <= target_address <= 0xFFFF):
                err_msg = f"Address '{target_address:X}' out of range for EXTENDED mode (0000-FFFF)."
                self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                return [], err_msg
            generated_bytes.append((target_address >> 8) & 0xFF) # High byte
            generated_bytes.append(target_address & 0xFF)        # Low byte
            actual_operand_byte_count = 2
        elif addressing_mode == MODE_INDEXED:
            # operand_value_from_parser 8-bit offset olmalı
            if not isinstance(operand_value_from_parser, int) or not (0 <= operand_value_from_parser <= 0xFF):
                err_msg = f"Invalid indexed offset for '{pi.mnemonic}': {operand_value_from_parser}. Expected 8-bit int."
                self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                return [], err_msg
            generated_bytes.append(operand_value_from_parser & 0xFF)
            actual_operand_byte_count = 1
        elif addressing_mode == MODE_RELATIVE:
            target_label = operand_value_from_parser
            if not isinstance(target_label, str): # Etiket olmalı
                err_msg = f"Operand for RELATIVE mode must be a label. Got: {target_label}"
                self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                return [], err_msg

            target_address = self.symbol_table.get_address(target_label)
            if target_address is None:
                err_msg = f"Undefined symbol '{target_label}' for branch instruction."
                self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                return [], err_msg

            current_instruction_address = pi.address # ParsedInstruction'a eklediğimiz adres
            # Relative offset: target_address - (current_instruction_address + instruction_length_for_branch)
            # Branch komutları genellikle 2 byte'tır (1 opkod + 1 offset).
            offset = target_address - (current_instruction_address + 2)

            if not (-128 <= offset <= 127):
                err_msg = f"Branch to '{target_label}' (addr {target_address:04X}) from {current_instruction_address:04X} is out of relative range (offset: {offset})."
                self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
                return [], err_msg
            generated_bytes.append(offset & 0xFF) # 2's complement ofset
            actual_operand_byte_count = 1
        elif addressing_mode == MODE_IMPLIED:
            # Operand yok, sadece opkod. actual_operand_byte_count = 0
            pass
        else:
            err_msg = f"Unsupported addressing mode '{addressing_mode}' for code generation of '{pi.mnemonic}'."
            self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
            return [], err_msg

        # Üretilen toplam byte sayısını kontrol et
        total_bytes_generated = 1 + actual_operand_byte_count # 1 opkod için
        if num_bytes_expected is not None and total_bytes_generated != num_bytes_expected:
            err_msg = (f"Byte count mismatch for '{pi.mnemonic}' in mode '{addressing_mode}'. "
                       f"Expected {num_bytes_expected}, Generated {total_bytes_generated}.")
            self._add_error(pi.token.line_number, err_msg, pi.token.original_line)
            # Hata durumunda üretilen byte'ları döndürmeyebiliriz veya olduğu gibi bırakabiliriz.
            # Şimdilik hatayı bildirip üretilenleri döndürelim.
            return generated_bytes, err_msg # Hata mesajını da döndür

        return generated_bytes, None # Başarılı, hata mesajı None

# Test için örnek kullanım (Assembler sınıfı içinden çağrılacak)
if __name__ == "__main__":
    # Bu sınıfı tek başına test etmek için mock nesneler oluşturmak gerekir.
    # Örnek:
    class MockOpcodeTable:
        def get_instruction_info(self, mnemonic):
            if mnemonic == "LDAA":
                return {
                    MODE_IMMEDIATE: {'opcode': 0x86, 'bytes': 2},
                    MODE_EXTENDED: {'opcode': 0xB6, 'bytes': 3}
                }
            return None
        def get_pseudo_op_info(self, directive):
            if directive == "FCB":
                return {'params': '1_or_more'}
            return None

    class MockParsedInstruction:
        def __init__(self, token, mnemonic, addressing_mode=None, operands=None, op_info=None, is_directive=False, error=None, address=0):
            self.token = token
            self.mnemonic = mnemonic
            self.addressing_mode = addressing_mode
            self.operands = operands if operands is not None else []
            self.op_info = op_info
            self.is_directive = is_directive
            self.error = error
            self.address = address # Komutun adresi (branch offset için)

    class MockToken:
        def __init__(self, line_number, original_line):
            self.line_number = line_number
            self.original_line = original_line

    st = SymbolTable()
    st.add_symbol("MYLABEL", 0x0150)

    cg = CodeGenerator(st, MockOpcodeTable())

    # Test 1: LDAA #$10
    token1 = MockToken(1, "LDAA #$10")
    pi1_opinfo = MockOpcodeTable().get_instruction_info("LDAA")[MODE_IMMEDIATE]
    pi1 = MockParsedInstruction(token1, "LDAA", MODE_IMMEDIATE, [0x10], pi1_opinfo, address=0x0100)
    code1, err1 = cg.generate_code_for_instruction(pi1)
    print(f"LDAA #$10 -> Code: {[hex(b) for b in code1]}, Error: {err1}") # Beklenen: [0x86, 0x10]

    # Test 2: LDAA MYLABEL (Extended)
    token2 = MockToken(2, "LDAA MYLABEL")
    pi2_opinfo = MockOpcodeTable().get_instruction_info("LDAA")[MODE_EXTENDED]
    pi2 = MockParsedInstruction(token2, "LDAA", MODE_EXTENDED, ["MYLABEL"], pi2_opinfo, address=0x0102)
    code2, err2 = cg.generate_code_for_instruction(pi2)
    print(f"LDAA MYLABEL -> Code: {[hex(b) for b in code2]}, Error: {err2}") # Beklenen: [0xB6, 0x01, 0x50]

    # Test 3: FCB $0A, MYLABEL
    token3 = MockToken(3, "FCB $0A, MYLABEL")
    # FCB için op_info'yu mocklamaya gerek yok, direktif adı yeterli.
    pi3 = MockParsedInstruction(token3, "FCB", operands=["$0A", "MYLABEL"], is_directive=True, address=0x0105)
    code3, err3 = cg.generate_code_for_instruction(pi3)
    print(f"FCB $0A, MYLABEL -> Code: {[hex(b) for b in code3]}, Error: {err3}") # Beklenen: [0x0A, 0x01, 0x50] (MYLABEL 0x0150 olduğu için 2 byte olarak yorumlanmamalı, FCB 1 byte alır)
    # FCB için düzeltme: FCB operandları tek byte'lık değerler olmalı. Eğer MYLABEL 0x0150 ise bu FCB için bir hata olmalı ya da sadece düşük byte'ı almalı.
    # Mevcut kodumda FCB için etiket çözümlemesi 0-255 aralığında olmalı.
    st.add_symbol("BYTE_LABEL", 0x20)
    pi3_corrected = MockParsedInstruction(token3, "FCB", operands=["$0A", "BYTE_LABEL"], is_directive=True, address=0x0105)
    code3_c, err3_c = cg.generate_code_for_instruction(pi3_corrected)
    print(f"FCB $0A, BYTE_LABEL -> Code: {[hex(b) for b in code3_c]}, Error: {err3_c}") # Beklenen: [0x0A, 0x20] 
