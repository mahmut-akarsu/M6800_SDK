import re
from .opcode_table import get_instruction_info, get_pseudo_op_info, MODE_IMPLIED, MODE_IMMEDIATE, MODE_DIRECT, MODE_EXTENDED, MODE_INDEXED, MODE_RELATIVE
from .lexical_analyzer import Token # Token sınıfını kullanacağız

class ParsedInstruction:
    """
    Sözdizimi analizinden geçmiş bir komutu veya direktifi temsil eder.
    Adresleme modu, çözümlenmiş operandlar gibi ek bilgiler içerir.
    """
    def __init__(self, token, is_directive=False, mnemonic=None, addressing_mode=None, operands=None, op_info=None, error=None, address=0): # address eklendi
        self.token = token # Orijinal Token nesnesi
        self.is_directive = is_directive
        self.mnemonic = mnemonic.upper() if mnemonic else (token.mnemonic.upper() if token.mnemonic else None)
        self.addressing_mode = addressing_mode
        self.operands = operands if operands is not None else [] # [(type, value), ...] veya direkt değer listesi
        self.op_info = op_info # opcode_table'dan gelen instruction/directive bilgisi
        self.error = error # Eğer syntax hatası varsa
        self.address = address # Komutun/direktifin Pass 1'deki adresi

    def __repr__(self):
        return (f"ParsedInstruction(Addr={self.address:04X}, Mnem='{self.mnemonic}', Mode='{self.addressing_mode}', "
                f"Ops={self.operands}, Err='{self.error}', Orig='{self.token.original_line}')")

class SyntaxAnalyzer:
    def __init__(self, opcode_table_module):
        self.opcode_table = opcode_table_module # opcode_table.py modülünün kendisi
        # Regex tanımları
        self.imm_regex = re.compile(r"^#(?:\$([0-9A-Fa-f]{1,2})|%([01]{1,8})|(\d{1,3})|'(.)')$")
        self.idx_regex = re.compile(r"^(?:\$([0-9A-Fa-f]{1,2})|(\d{1,3})),\s*X$", re.IGNORECASE)
        self.hex_addr_regex = re.compile(r"^\$([0-9A-Fa-f]{1,4})$")
        self.label_regex = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)$")
        self.dec_num_regex = re.compile(r"^(\d+)$")

        self.value_list_regex = re.compile(r"\s*,\s*")


    def _parse_operand_value(self, operand_str):
        operand_str = operand_str.strip()

        # 1. Anında Değerler (# ile başlar)
        m_imm = self.imm_regex.match(operand_str)
        if m_imm:
            if m_imm.group(1): return 'imm_hex', int(m_imm.group(1), 16)
            elif m_imm.group(2): return 'imm_bin', int(m_imm.group(2), 2)
            elif m_imm.group(3): return 'imm_dec', int(m_imm.group(3))
            elif m_imm.group(4): return 'imm_char', ord(m_imm.group(4))
            return 'error', "Invalid immediate format"

        # 2. İndeksli Değerler (,X ile biter)
        m_idx = self.idx_regex.match(operand_str)
        if m_idx:
            offset_val = None
            if m_idx.group(1): offset_val = int(m_idx.group(1), 16) # Hex offset
            elif m_idx.group(2): offset_val = int(m_idx.group(2))   # Decimal offset
            if offset_val is not None and 0 <= offset_val <= 255:
                return 'indexed', offset_val
            else:
                return 'error', f"Invalid or out-of-range indexed offset: {operand_str}"

        # 3. Hex Adres ($ ile başlar)
        m_hex_addr = self.hex_addr_regex.match(operand_str)
        if m_hex_addr:
            hex_val_str = m_hex_addr.group(1)
            val = int(hex_val_str, 16)
            # Adres aralığına göre direct/extended ayrımı CodeGenerator'da yapılmalı.
            # Şimdilik sadece hex adres olduğunu belirtelim.
            # if len(hex_val_str) <= 2 and 0 <= val <= 0xFF: return 'address_direct_hex', val
            # elif 0 <= val <= 0xFFFF: return 'address_extended_hex', val
            if 0 <= val <= 0xFFFF: return 'hex_address', val # Genel hex adres tipi
            else: return 'error', f"Hex address out of 16-bit range: {operand_str}"

        # 4. Düz Decimal Sayı (Sadece rakamlardan oluşuyorsa)
        m_dec_num = self.dec_num_regex.match(operand_str)
        if m_dec_num:
            val = int(m_dec_num.group(1))
            # Komutlar için bu adres olabilir, direktifler için sayı.
            return 'decimal_value', val

        # 5. Etiket (Diğerlerine uymuyorsa ve geçerli etiket formatındaysa)
        m_label = self.label_regex.match(operand_str)
        if m_label:
            return 'label', m_label.group(1).upper()

        return 'unknown', operand_str # Hiçbirine uymadıysa

    def _parse_operands_string(self, operands_raw_str):
        """Ham operand string'ini [(type, value), ...] listesine çevirir."""
        parsed_ops_list_of_tuples = []
        if not operands_raw_str:
            return parsed_ops_list_of_tuples

        op_parts = [op.strip() for op in self.value_list_regex.split(operands_raw_str) if op.strip()]

        for op_str in op_parts:
            op_type, op_value = self._parse_operand_value(op_str)
            if op_type == 'error':
                # Hata varsa, hatalı değeri ve mesajı içeren tek bir tuple döndür.
                return [('error', op_value)]
            parsed_ops_list_of_tuples.append((op_type, op_value))
        return parsed_ops_list_of_tuples


    def parse_token(self, token: Token):
        if not token.mnemonic:
            if token.label and not token.comment and not token.operands_raw_str:
                return ParsedInstruction(token, mnemonic=None)
            elif token.comment:
                return ParsedInstruction(token, mnemonic=None)
            return ParsedInstruction(token, error="Missing mnemonic/directive.")

        mnemonic = token.mnemonic.upper()
        op_info_instr = self.opcode_table.get_instruction_info(mnemonic)
        op_info_pseudo = self.opcode_table.get_pseudo_op_info(mnemonic)

        if op_info_instr: # Bu bir M6800 komutu
            parsed_ops_tuples = self._parse_operands_string(token.operands_raw_str)

            if parsed_ops_tuples and parsed_ops_tuples[0][0] == 'error':
                return ParsedInstruction(token, mnemonic=mnemonic, error=f"Operand error: {parsed_ops_tuples[0][1]}")

            addressing_mode = None
            # Komutlar genellikle tek operand alır veya implied'dır.
            # ParsedInstruction.operands sadece çözümlenmiş değeri (veya etiket adını) tutacak.
            final_operand_value = None
            if parsed_ops_tuples:
                final_operand_value = parsed_ops_tuples[0][1] # İlk operandın değeri
                op_type = parsed_ops_tuples[0][0]

                if op_type.startswith('imm_') and MODE_IMMEDIATE in op_info_instr:
                    addressing_mode = MODE_IMMEDIATE
                elif op_type == 'indexed' and MODE_INDEXED in op_info_instr:
                    addressing_mode = MODE_INDEXED
                elif op_type == 'label':
                    if MODE_RELATIVE in op_info_instr: addressing_mode = MODE_RELATIVE
                    # Etiket direct/extended için olabilir. Bu ayrım Pass2/CodeGen'de yapılır.
                    # Şimdilik komutun bu tür adreslemeyi desteklediğini varsayalım.
                    elif MODE_EXTENDED in op_info_instr: addressing_mode = MODE_EXTENDED
                    elif MODE_DIRECT in op_info_instr: addressing_mode = MODE_DIRECT
                    else: return ParsedInstruction(token, mnemonic=mnemonic, error=f"Label operand not supported by {mnemonic}")
                elif op_type == 'hex_address' or op_type == 'decimal_value': # $XXXX or DDDD
                    # Adresin direct mi extended mı olduğuna Pass2/CodeGen karar verir.
                    # Komutun bu tür adreslemeyi desteklediğini kontrol et.
                    if MODE_EXTENDED in op_info_instr: addressing_mode = MODE_EXTENDED
                    elif MODE_DIRECT in op_info_instr: addressing_mode = MODE_DIRECT
                    else: return ParsedInstruction(token, mnemonic=mnemonic, error=f"Numeric address not supported by {mnemonic}")
                # Diğer op_type'lar için hata
                elif addressing_mode is None : # Eşleşen mod yoksa
                     return ParsedInstruction(token, mnemonic=mnemonic, error=f"Invalid operand type '{op_type}' for {mnemonic}")


            elif MODE_IMPLIED in op_info_instr: # Operand yoksa ve Implied destekleniyorsa
                addressing_mode = MODE_IMPLIED
            # Hiç operand yoksa ama komut Implied değilse hata (aşağıda)

            if addressing_mode:
                mode_specific_op_info = op_info_instr.get(addressing_mode)
                if mode_specific_op_info:
                    return ParsedInstruction(token, mnemonic=mnemonic, addressing_mode=addressing_mode,
                                             operands=[final_operand_value] if final_operand_value is not None else [],
                                             op_info=mode_specific_op_info)
                else: # Bu olmamalı, adresleme modu op_info_instr'da olmalı
                    return ParsedInstruction(token, mnemonic=mnemonic, error=f"Internal: Mode '{addressing_mode}' inconsistent for '{mnemonic}'.")
            else:
                expected_modes = ", ".join(op_info_instr.keys())
                return ParsedInstruction(token, mnemonic=mnemonic, op_info=op_info_instr,
                                         error=f"Invalid/missing operands for '{mnemonic}'. Expected: {expected_modes}. Got: '{token.operands_raw_str or 'None'}'")

        elif op_info_pseudo: # Bu bir assembler direktifi
            directive_operands = [] # Direktifler için operandlar değer listesi olarak saklanacak
            error_msg = None
            op_parts_tuples = []
            if token.operands_raw_str:
                op_parts_tuples = self._parse_operands_string(token.operands_raw_str)
                if op_parts_tuples and op_parts_tuples[0][0] == 'error':
                    return ParsedInstruction(token, is_directive=True, mnemonic=mnemonic, op_info=op_info_pseudo, error=f"Operand error: {op_parts_tuples[0][1]}")

            # Direktiflere özel operand işleme
            if mnemonic == 'EQU':
                if token.label and len(op_parts_tuples) == 1:
                    op_type, op_val = op_parts_tuples[0]
                    if op_type not in ['error', 'unknown', 'indexed']: # EQU sayı, hex adres, etiket alabilir
                        directive_operands.append(op_val)
                    else: error_msg = f"Invalid value for EQU: type '{op_type}' for '{op_val}'"
                else: error_msg = "EQU directive requires a label and exactly one value operand."
            elif mnemonic in ['FCB', 'FDB']:
                for op_type, op_val in op_parts_tuples:
                    if op_type.startswith('imm_') or op_type == 'hex_address' or op_type == 'decimal_value' or op_type == 'label':
                        directive_operands.append(op_val)
                    else: error_msg = f"Invalid value type '{op_type}' for {mnemonic} operand '{op_val}'"; break
            elif mnemonic == 'RMB' or mnemonic == 'ORG':
                if len(op_parts_tuples) == 1:
                    op_type, op_val = op_parts_tuples[0]
                    if op_type == 'decimal_value' or op_type == 'hex_address' or op_type == 'label':
                        if op_type == 'decimal_value' and not (isinstance(op_val, int) and op_val >=0):
                             error_msg = f"{mnemonic} expects a non-negative integer, got '{op_val}'"
                        else:
                            directive_operands.append(op_val)
                    else: error_msg = f"Invalid value type '{op_type}' for {mnemonic}: '{op_val}'"
                else: error_msg = f"{mnemonic} directive expects 1 argument."
            elif mnemonic == 'END':
                if op_parts_tuples: error_msg = "END directive does not take arguments."
            # Diğer direktifler eklenebilir

            # Operand sayısı kontrolü
            if not error_msg:
                expected_params_info = op_info_pseudo.get('params', 0)
                num_parsed_ops = len(directive_operands) # directive_operands artık sadece değerleri içeriyor

                if isinstance(expected_params_info, int):
                    if not (mnemonic == 'END' and num_parsed_ops == 0 and not token.operands_raw_str):
                        if num_parsed_ops != expected_params_info:
                            error_msg = f"Directive '{mnemonic}' expects {expected_params_info} operand(s), got {num_parsed_ops}."
                elif expected_params_info == '1_or_more':
                    if num_parsed_ops == 0 and token.operands_raw_str : # Operand vardı ama parse edilemediyse farklı, hiç yoksa farklı
                         error_msg = f"Directive '{mnemonic}' expects at least 1 operand, but none were validly parsed."
                    elif num_parsed_ops == 0 and not token.operands_raw_str:
                         error_msg = f"Directive '{mnemonic}' expects at least 1 operand, none provided."


            if error_msg:
                return ParsedInstruction(token, is_directive=True, mnemonic=mnemonic, op_info=op_info_pseudo, error=error_msg)
            else:
                return ParsedInstruction(token, is_directive=True, mnemonic=mnemonic, operands=directive_operands, op_info=op_info_pseudo)

        else: # Ne komut ne de direktif
            return ParsedInstruction(token, error=f"Unknown mnemonic or directive: '{mnemonic}'")

    def parse_tokens(self, token_list):
        parsed_instructions = []
        for token_obj in token_list: # token_obj olarak değiştirdim, token modülüyle karışmasın
            parsed_instructions.append(self.parse_token(token_obj))
        return parsed_instructions


# Test için örnek kullanım
if __name__ == "__main__":
    from .lexical_analyzer import LexicalAnalyzer
    import assembler.opcode_table as ot_module # opcode_table.py 'yi import et

    lexer = LexicalAnalyzer()
    syntax_analyzer = SyntaxAnalyzer(ot_module) # ot_module'ü constructor'a ver

    sample_code = """
    START EQU $1000
    LOOP: LDAA #$05
          RMB  1         ; Test RMB
          ORG  $C000
          FCB  $0A, 20, %00010101, #'X', START
          END
    BADRMB RMB BADVAL
    """
    print("--- Parsing Sample Code ---")
    tokens = lexer.tokenize_source_code(sample_code)
    parsed_instrs = syntax_analyzer.parse_tokens(tokens)

    for pi in parsed_instrs:
        print(pi)