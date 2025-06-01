from .lexical_analyzer import LexicalAnalyzer
from .syntax_analyzer import SyntaxAnalyzer, ParsedInstruction
from .symbol_table import SymbolTable
from .opcode_table import get_pseudo_op_info, MODE_DIRECT, MODE_EXTENDED, MODE_RELATIVE
import assembler.opcode_table as ot_module
from .code_generator import CodeGenerator # CodeGenerator'ı import et

# CodeGenerator'ı daha sonra import edeceğiz
# from .code_generator import CodeGenerator

class Assembler:
    def __init__(self):
        self.lexer = LexicalAnalyzer()
        self.syntax_analyzer = SyntaxAnalyzer(ot_module) # ot_module burada kullanılıyor
        self.symbol_table = SymbolTable()
        self.code_generator = CodeGenerator(self.symbol_table, ot_module) # CodeGenerator'ı initialize et
        self.location_counter = 0
        self.program_origin = 0 # ORG ile set edilecek
        self.parsed_instructions = [] # Syntax analizinden geçmiş talimatlar
        self.object_code = [] # Üretilen byte listesi
        self.errors = []
        self.listing = [] # (adres, hex_kod, kaynak_satır) tuple listesi

    def _add_error(self, line_number, message, original_line=""):
        self.errors.append(f"Error (L:{line_number}): {message} -> '{original_line}'")

    def _reset_state(self):
        self.symbol_table.clear()
        self.location_counter = 0
        self.program_origin = 0
        self.parsed_instructions = []
        self.object_code = []
        self.errors = []
        self.listing = []

    def assemble_pass1(self, source_code_str):
        """
        Assembler'ın birinci geçişi.
        - Kaynak kodu token'lara ve sonra parsed instruction'lara çevirir.
        - Sembol tablosunu (etiketler ve adresleri) oluşturur.
        - Her komutun yaklaşık uzunluğunu hesaplar (LC'yi yönetir).
        """
        self.parsed_instructions = [] # Her assemble çağrısında temizle
        self.location_counter = self.program_origin # LC, ORG ile başlar

        tokens = self.lexer.tokenize_source_code(source_code_str)
        parsed_instructions_temp = self.syntax_analyzer.parse_tokens(tokens)

        current_lc_for_instruction = self.location_counter

        for pi in parsed_instructions_temp:
            pi.address = current_lc_for_instruction # Her parsed instruction'a o anki LC'yi ekleyelim
            self.parsed_instructions.append(pi) # Hatalı olsa bile listeye ekle, Pass2'de atlanabilir

            if pi.error:
                self._add_error(pi.token.line_number, pi.error, pi.token.original_line)
                # Hatalı komutlar için LC ilerletme konusunda dikkatli olmalı, şimdilik atlayalım
                # veya varsayılan bir uzunluk ekleyebiliriz.
                # Şimdilik hatalı komutun LC'yi etkilemediğini varsayalım.
                continue # Hata varsa LC ilerletme ve sembol ekleme yapma

            # 1. Etiket Varsa Sembol Tablosuna Ekle
            if pi.token.label:
                if self.symbol_table.has_symbol(pi.token.label):
                    self._add_error(pi.token.line_number, f"Label '{pi.token.label}' redefined.", pi.token.original_line)
                else:
                    self.symbol_table.add_symbol(pi.token.label, current_lc_for_instruction)

            # 2. LC'yi Güncelle
            if pi.is_directive:
                directive_name = pi.mnemonic.upper()
                pseudo_op_info = get_pseudo_op_info(directive_name) # opcode_table'dan al

                if directive_name == 'ORG':
                    if pi.operands:
                        # Operandın sayısal bir değer veya çözümlenebilir bir etiket olması lazım.
                        # Şimdilik sadece sayısal değeri destekleyelim. Etiket çözümü Pass2'de.
                        try:
                            new_origin = int(str(pi.operands[0]), 0) # Hex ($) veya decimal olabilir
                            self.location_counter = new_origin
                            self.program_origin = new_origin
                            current_lc_for_instruction = new_origin # ORG sonrası LC'yi güncelle
                        except ValueError:
                            self._add_error(pi.token.line_number, f"Invalid ORG value: {pi.operands[0]}", pi.token.original_line)
                    else:
                        self._add_error(pi.token.line_number, "ORG directive requires an address.", pi.token.original_line)
                elif directive_name == 'EQU':
                    # EQU LC'yi etkilemez, sadece sembol tablosuna değer atar.
                    # Etiket (pi.token.label) ve değer (pi.operands[0]) olmalı.
                    if pi.token.label and pi.operands:
                        try:
                            # EQU değeri sayı veya başka bir etiket olabilir.
                            # Şimdilik sadece sayısal değerleri destekleyelim.
                            equ_value_str = str(pi.operands[0])
                            equ_value = 0
                            if equ_value_str.startswith('$'):
                                equ_value = int(equ_value_str[1:], 16)
                            elif equ_value_str.startswith('%'):
                                equ_value = int(equ_value_str[1:], 2)
                            else: # Decimal veya etiket olabilir. Şimdilik decimal.
                                equ_value = int(equ_value_str)

                            # Sembol tablosuna normal adres gibi değil, sabit değer olarak ekleyebiliriz.
                            # Ya da SymbolTable sınıfını buna göre modifiye edebiliriz.
                            # Şimdilik normal adres gibi ekliyoruz.
                            if self.symbol_table.has_symbol(pi.token.label):
                                self._add_error(pi.token.line_number, f"Label '{pi.token.label}' (for EQU) redefined.", pi.token.original_line)
                            else:
                                self.symbol_table.add_symbol(pi.token.label, equ_value)
                        except ValueError:
                            self._add_error(pi.token.line_number, f"Invalid EQU value: {pi.operands[0]}", pi.token.original_line)
                    else:
                         self._add_error(pi.token.line_number, "EQU directive requires a label and a value.", pi.token.original_line)

                elif directive_name == 'FCB': # Form Constant Byte(s)
                    # Operandlar byte değerleri listesi olmalı
                    current_lc_for_instruction += len(pi.operands) # Her operand bir byte
                elif directive_name == 'FDB': # Form Double Byte(s) / WORD
                    current_lc_for_instruction += len(pi.operands) * 2 # Her operand iki byte
                elif directive_name == 'RMB': # Reserve Memory Bytes
                    if pi.operands:
                        try:
                            num_bytes = int(str(pi.operands[0]), 0)
                            current_lc_for_instruction += num_bytes
                        except ValueError:
                            self._add_error(pi.token.line_number, f"Invalid RMB value: {pi.operands[0]}", pi.token.original_line)
                    else:
                        self._add_error(pi.token.line_number, "RMB directive requires a count.", pi.token.original_line)
                elif directive_name == 'END':
                    # Program sonu, LC'yi etkilemez ama Pass1'i bitirebilir.
                    break # END sonrası satırları işlemeyi durdur
                # Diğer direktifler (varsa) LC'yi etkilemeyebilir.

            elif pi.mnemonic and pi.op_info: # M6800 komutu
                # op_info, syntax_analyzer tarafından belirlenen moda özgü bilgiyi içerir.
                # (opcode, bytes, ...)
                instruction_length = pi.op_info.get('bytes', 0) # Varsayılan 0 eğer byte bilgisi yoksa
                if instruction_length == 0:
                    # Bu bir hata olabilir, opcode_table'da byte bilgisi eksik.
                    self._add_error(pi.token.line_number, f"Byte length not found for instruction '{pi.mnemonic}' in mode '{pi.addressing_mode}'.", pi.token.original_line)
                current_lc_for_instruction += instruction_length
            # LC'yi bir sonraki komutun adresi olacak şekilde güncelle
            self.location_counter = current_lc_for_instruction


        # Pass 1 sonunda, eğer hatalar varsa, bunları döndür veya sakla
        return not self.errors # Başarılıysa True, değilse False


    def assemble_pass2(self):
        """
        Assembler'ın ikinci geçişi. (CodeGenerator kullanarak güncellendi)
        """
        if self.errors and any("Pass 1" in err for err in self.errors): # Pass 1'de kritik hata varsa
            # self._add_error(0, "Critical errors in Pass 1. Aborting Pass 2.", "SYSTEM") # Veya print
            return False

        # Pass 2'ye özel hatalar için listeyi temizle veya ayrı bir liste tut
        # Şimdilik genel self.errors'a eklemeye devam edelim.
        # pass2_errors = []

        self.object_code = []
        self.listing = []
        # current_address_in_object_code = self.program_origin # Bu, listing için LC'yi takip etmeli

        for pi in self.parsed_instructions:
            # Her komutun listing için adresini al (Pass 1'de set edilmiş olmalı)
            current_lc_for_listing = pi.address if hasattr(pi, 'address') else self.program_origin # Varsayılan

            if pi.error: # Syntax analizinden gelen hata
                # Bu hatayı CodeGenerator üretmese bile listing'e ekleyelim
                self.listing.append((f"{current_lc_for_listing:04X}", "ERROR", pi.token.original_line, pi.error))
                # self.errors'a zaten Pass1'de eklenmiş olabilir, tekrar eklemeyebiliriz.
                continue

            generated_bytes, codegen_error_msg = self.code_generator.generate_code_for_instruction(pi)

            if codegen_error_msg:
                self._add_error(pi.token.line_number, codegen_error_msg, pi.token.original_line)
                self.listing.append((f"{current_lc_for_listing:04X}", "CG_ERR", pi.token.original_line, codegen_error_msg))
                # Hata varsa, bu komut için nesne kodu eklenmemeli
                continue # Bir sonraki komuta geç

            # Direktifler için özel listeleme (ORG, EQU, RMB, END byte üretmez)
            if pi.is_directive:
                directive_name = pi.mnemonic.upper()
                directive_comment = ""
                if directive_name == 'ORG':
                    directive_comment = f"; ORG to ${pi.operands[0]:04X}" if pi.operands else "; ORG"
                    # ORG nesne kodu üretmez, ama sonraki adresleri etkiler
                    # self.program_origin = pi.operands[0] # Bu Pass1'de yapıldı, burada tekrar gerek yok
                elif directive_name == 'EQU':
                    directive_comment = f"; {pi.token.label} EQU {pi.operands[0]}" # Değer hex/dec olabilir
                elif directive_name == 'RMB':
                    directive_comment = f"; RMB {pi.operands[0]} byte(s)"
                elif directive_name == 'END':
                    directive_comment = "; END of program"

                if generated_bytes: # FCB, FDB gibi byte üreten direktifler
                    hex_code_str = " ".join([f"{b:02X}" for b in generated_bytes])
                    self.listing.append((f"{current_lc_for_listing:04X}", hex_code_str, pi.token.original_line, directive_comment))
                    self.object_code.extend(generated_bytes)
                else: # Byte üretmeyen direktifler (ORG, EQU, RMB, END)
                    self.listing.append((f"{current_lc_for_listing:04X}", "      ", pi.token.original_line, directive_comment))

                if directive_name == 'END':
                    break # Program sonu
                continue # Bir sonraki talimata geç

            # M6800 Komutları için listeleme
            if generated_bytes:
                self.object_code.extend(generated_bytes)
                hex_code_str = " ".join([f"{b:02X}" for b in generated_bytes])
                self.listing.append((f"{current_lc_for_listing:04X}", hex_code_str, pi.token.original_line, ""))
            elif not pi.error: # Kod üretmeyen ama hata da olmayan (örn. sadece etiket)
                 self.listing.append((f"{current_lc_for_listing:04X}", "      ", pi.token.original_line, "; No object code"))


        # CodeGenerator'dan gelen hataları ana hata listesine ekleyebiliriz
        # self.errors.extend(self.code_generator.errors) # Eğer CodeGenerator kendi listesini tutuyorsa

        return not any(err for err in self.errors if "Error" in err or "CodeGen Error" in err) # Kritik hata var mı kontrol et

    def assemble(self, source_code_str):
        """
        Tüm assembler sürecini yönetir.
        """
        self._reset_state()
        if not self.assemble_pass1(source_code_str):
            print("Assembly failed in Pass 1.")
            # self.listing'e hataları ekleyebiliriz
            for error_msg in self.errors:
                # Hata mesajından satır numarasını ayrıştırmak gerekebilir.
                # Şimdilik genel bir hata olarak ekleyelim.
                self.listing.append(("----", "ERROR", "", error_msg))

            return False, self.object_code, self.listing, self.errors

        if not self.assemble_pass2():
            print("Assembly failed in Pass 2.")
            # Pass 2 hataları zaten self.errors ve self.listing'e eklenmiş olmalı
            return False, self.object_code, self.listing, self.errors

        print("Assembly successful.")
        return True, self.object_code, self.listing, self.errors

# Test için örnek kullanım
if __name__ == "__main__":
    assembler = Assembler()
    sample_code = """
    STARTADR EQU $0100    ; Program başlangıç adresi
             ORG  STARTADR
    LOOP     LDAA #$05      ; A'ya 5 yükle
             DECA
             BNE  LOOP      ; LOOP'a dallan eğer sıfır değilse
             LDAB DATA_VAL
             STAA RESULT,X
             JMP  LOOP
    DATA_VAL FCB  $FF
    RESULT   RMB  1
             END
    """
    # İkinci bir örnek, hatalı
    sample_code_error = """
             ORG $C000
    MYLOOP   LDAA #$AA
             ADDB UNKNOWN_LABEL ; Tanımsız etiket
             BNE  MYLOOP
    ENDIT    EQU  MYLOOP ; Bu geçerli
             END
    """

    print("--- Assembling Sample Code 1 ---")
    success, obj_code, listing_output, errors_output = assembler.assemble(sample_code)
    if success:
        print("Object Code:", ["0x{:02X}".format(b) for b in obj_code])
        print("\nListing:")
        for addr, code, src, err_cmt in listing_output:
            print(f"{addr}\t{code:<10}\t{src:<30}\t{err_cmt}")
    else:
        print("\nErrors:")
        for err in errors_output:
            print(err)
        print("\nPartial Listing with Errors:")
        for addr, code, src, err_cmt in listing_output:
            print(f"{addr}\t{code:<10}\t{src:<30}\t{err_cmt}")


    print("\n\n--- Assembling Sample Code 2 (with errors) ---")
    success2, obj_code2, listing_output2, errors_output2 = assembler.assemble(sample_code_error)
    if not success2:
        print("Object Code (if any):", ["0x{:02X}".format(b) for b in obj_code2])
        print("\nErrors:")
        for err in errors_output2:
            print(err)
        print("\nListing with Errors:")
        for addr, code, src, err_cmt in listing_output2:
            print(f"{addr}\t{code:<10}\t{src:<30}\t{err_cmt}") 
