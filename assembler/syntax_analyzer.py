import re
from .opcode_table import get_instruction_info, get_pseudo_op_info, MODE_IMPLIED, MODE_IMMEDIATE, MODE_DIRECT, MODE_EXTENDED, MODE_INDEXED, MODE_RELATIVE
from .lexical_analyzer import Token # Token sınıfını kullanacağız

class ParsedInstruction:
    """
    Sözdizimi analizinden geçmiş bir komutu veya direktifi temsil eder.
    Adresleme modu, çözümlenmiş operandlar gibi ek bilgiler içerir.
    """
    def __init__(self, token, is_directive=False, mnemonic=None, addressing_mode=None, operands=None, op_info=None, error=None):
        self.token = token # Orijinal Token nesnesi
        self.is_directive = is_directive
        self.mnemonic = mnemonic.upper() if mnemonic else (token.mnemonic.upper() if token.mnemonic else None)
        self.addressing_mode = addressing_mode
        self.operands = operands if operands is not None else [] # [(type, value), ...]
        self.op_info = op_info # opcode_table'dan gelen instruction/directive bilgisi
        self.error = error # Eğer syntax hatası varsa

    def __repr__(self):
        return (f"ParsedInstruction(Mnem='{self.mnemonic}', Mode='{self.addressing_mode}', "
                f"Ops={self.operands}, Err='{self.error}', OrigToken={self.token})")

class SyntaxAnalyzer:
    def __init__(self, opcode_table_module):
        self.opcode_table = opcode_table_module
        # Operandları ayrıştırmak için regex'ler
        # Anında (Immediate): #$xx, #%bb, #dd, #'c'
        self.imm_regex = re.compile(r"^#(?:\$([0-9A-Fa-f]{1,2})|%([01]{1,8})|(\d{1,3})|'(.)')$") # Hex, Binary, Decimal, Char
        # İndeksli (Indexed): offset,X  (offset 0-255 arası bir byte)
        self.idx_regex = re.compile(r"^(?:\$([0-9A-Fa-f]{1,2})|(\d{1,3})),\s*X$", re.IGNORECASE) # Hex offset, Decimal offset
        # Doğrudan (Direct) veya Genişletilmiş (Extended) veya Etiket: $xx, $xxxx, LABEL
        # Direct: $00-$FF (1 byte adres), Extended: $0100-$FFFF (2 byte adres)
        # Etiketler alfanumerik
        self.addr_label_regex = re.compile(r"^(?:\$([0-9A-Fa-f]{1,4})|([a-zA-Z_][a-zA-Z0-9_]*))$")

        # FCB/FDB için değerleri ayırma
        self.value_list_regex = re.compile(r"\s*,\s*")


    def _parse_operand_value(self, operand_str):
        """
        Verilen operand string'ini (örn: #$0A, $10, LOOP) sayısal değere veya etiket adına çevirmeye çalışır.
        Döndürülen değer: (type, value) tuple'ı. type: 'hex', 'dec', 'bin', 'char', 'label'
        """
        operand_str = operand_str.strip()

        # Anında Değerler
        m_imm = self.imm_regex.match(operand_str)
        if m_imm:
            if m_imm.group(1): # Hex
                return 'imm_hex', int(m_imm.group(1), 16)
            elif m_imm.group(2): # Binary
                return 'imm_bin', int(m_imm.group(2), 2)
            elif m_imm.group(3): # Decimal
                val = int(m_imm.group(3))
                if not (0 <= val <= 255): # M6800 immediate genellikle 1 byte
                     # print(f"Warning: Immediate decimal value {val} out of 8-bit range.") # Ya da hata
                     pass
                return 'imm_dec', val
            elif m_imm.group(4): # Character
                return 'imm_char', ord(m_imm.group(4))
            return 'error', "Invalid immediate format"

        # İndeksli Değerler (offset,X)
        m_idx = self.idx_regex.match(operand_str)
        if m_idx:
            offset_val = None
            if m_idx.group(1): # Hex offset
                offset_val = int(m_idx.group(1), 16)
            elif m_idx.group(2): # Decimal offset
                offset_val = int(m_idx.group(2))

            if offset_val is not None and 0 <= offset_val <= 255:
                return 'indexed', offset_val
            else:
                return 'error', f"Invalid or out-of-range indexed offset: {operand_str}"

        # Adres veya Etiket
        m_addr = self.addr_label_regex.match(operand_str)
        if m_addr:
            if m_addr.group(1): # Hex adres ($xxxx veya $xx)
                hex_val = m_addr.group(1)
                val = int(hex_val, 16)
                if len(hex_val) <= 2 and 0 <= val <= 0xFF: # Direct candidate
                    return 'address_direct_hex', val
                elif 0 <= val <= 0xFFFF: # Extended candidate
                    return 'address_extended_hex', val
                else:
                    return 'error', f"Hex address out of range: {operand_str}"
            elif m_addr.group(2): # Etiket
                return 'label', m_addr.group(2).upper()
            return 'error', "Invalid address/label format"

        return 'unknown', operand_str # Tanımlanamayan format

    def _parse_operands_string(self, operands_raw_str):
        """
        Ham operand string'ini (virgülle ayrılmış olabilir) [(type, value), ...] listesine çevirir.
        """
        parsed_ops = []
        if not operands_raw_str:
            return parsed_ops

        # FCB, FDB gibi direktifler birden fazla, virgülle ayrılmış değer alabilir
        # Şimdilik basitçe tek operandı veya virgülle ayrılmış listeyi varsayıyoruz
        # M6800'de çoğu komut en fazla 1 operand alır (JSR/JMP hariç, o da tek adres).
        # FCB, FDB özel durum.
        # Şimdilik sadece tek bir operandı ayrıştırmaya odaklanalım.
        # Birden fazla operand alan komutlar için bu kısım geliştirilmeli.

        # Basitçe, virgülle ayrılmışsa ilkini alalım veya özel direktifleri düşünelim.
        # Bu kısım, direktiflere göre daha akıllı olmalı.
        # Şimdilik tek operand veya ilk operandı alıyoruz.
        # M6800'de A,X veya B,X gibi operandlar yok. Sadece OFFSET,X var.

        op_parts = [op.strip() for op in self.value_list_regex.split(operands_raw_str) if op.strip()]

        for op_str in op_parts:
            op_type, op_value = self._parse_operand_value(op_str)
            if op_type == 'error':
                return [('error', op_value)] # Hata varsa hemen dön
            parsed_ops.append((op_type, op_value))
        return parsed_ops


    def parse_token(self, token: Token):
        """
        LexicalAnalyzer'dan gelen tek bir Token'ı analiz eder.
        ParsedInstruction nesnesi döndürür.
        """
        if not token.mnemonic: # Etiket veya yorum satırı, mnemonik yok
            if token.label and not token.comment and not token.operands_raw_str: # Sadece etiket var, başka bir şey yok
                return ParsedInstruction(token, mnemonic=None) # Geçerli, sadece etiket
            elif token.comment: # Yorum satırıysa veya etiketli yorumsa
                 return ParsedInstruction(token, mnemonic=None) # Geçerli
            return ParsedInstruction(token, error="Missing mnemonic/directive.")


        mnemonic = token.mnemonic.upper()
        op_info_instr = self.opcode_table.get_instruction_info(mnemonic)
        op_info_pseudo = self.opcode_table.get_pseudo_op_info(mnemonic)

        if op_info_instr: # Bu bir M6800 komutu
            parsed_ops_list = self._parse_operands_string(token.operands_raw_str)
            if parsed_ops_list and parsed_ops_list[0][0] == 'error':
                return ParsedInstruction(token, mnemonic=mnemonic, error=f"Invalid operand format: {parsed_ops_list[0][1]}")

            # Adresleme modunu belirle
            addressing_mode = None
            final_operands_for_instr = []

            # 1. Implied Modu
            if MODE_IMPLIED in op_info_instr:
                if not token.operands_raw_str: # Operand yoksa implied olabilir
                    addressing_mode = MODE_IMPLIED
                # Bazı implied komutlar (ASLA, ROLA) operand almaz ama token.operands_raw_str dolu olabilir (yorum vs).
                # Bu yüzden önce op_info_instr[MODE_IMPLIED] var mı diye bakmak daha doğru.
                # Eğer komut sadece Implied ise ve operand varsa bu bir hatadır.
                elif not parsed_ops_list: # Token.operands_raw_str dolu ama parse edilemediyse (sadece yorum gibi)
                    addressing_mode = MODE_IMPLIED


            # 2. Diğer Modlar (Operandlara göre)
            if not addressing_mode and parsed_ops_list:
                op_type, op_value = parsed_ops_list[0] # Şimdilik ilk operandı alıyoruz

                if op_type.startswith('imm_') and MODE_IMMEDIATE in op_info_instr:
                    addressing_mode = MODE_IMMEDIATE
                    final_operands_for_instr = [op_value] # Sadece değeri sakla
                elif op_type == 'indexed' and MODE_INDEXED in op_info_instr:
                    addressing_mode = MODE_INDEXED
                    final_operands_for_instr = [op_value] # Sadece offset'i sakla
                elif op_type == 'label':
                    # Etiket hem Direct/Extended (adres) hem de Relative (offset) için olabilir.
                    # Öncelik Relative (branch komutları)
                    if MODE_RELATIVE in op_info_instr:
                        addressing_mode = MODE_RELATIVE
                        final_operands_for_instr = [op_value] # Etiket adı
                    elif MODE_EXTENDED in op_info_instr: # Extended genellikle Direct'ten sonra gelir
                        addressing_mode = MODE_EXTENDED # Geçici olarak Extended, Pass 1 sonrası Direct'e düşebilir
                        final_operands_for_instr = [op_value]
                    elif MODE_DIRECT in op_info_instr:
                        addressing_mode = MODE_DIRECT
                        final_operands_for_instr = [op_value]
                    else:
                         return ParsedInstruction(token, mnemonic=mnemonic, op_info=op_info_instr,
                                                 error=f"Label '{op_value}' used with instruction '{mnemonic}' that does not support label addressing.")
                elif op_type == 'address_direct_hex':
                    if MODE_DIRECT in op_info_instr:
                        addressing_mode = MODE_DIRECT
                        final_operands_for_instr = [op_value]
                    elif MODE_EXTENDED in op_info_instr: # Direct yoksa Extended olabilir
                        addressing_mode = MODE_EXTENDED
                        final_operands_for_instr = [op_value]
                    else:
                        return ParsedInstruction(token, mnemonic=mnemonic, op_info=op_info_instr,
                                                 error=f"Direct address used with instruction '{mnemonic}' that does not support it.")
                elif op_type == 'address_extended_hex':
                    if MODE_EXTENDED in op_info_instr:
                        addressing_mode = MODE_EXTENDED
                        final_operands_for_instr = [op_value]
                    else:
                        return ParsedInstruction(token, mnemonic=mnemonic, op_info=op_info_instr,
                                                 error=f"Extended address used with instruction '{mnemonic}' that does not support it.")

            # Eğer operand yoksa ve Implied modu varsa ve başka mod yoksa
            if not parsed_ops_list and not token.operands_raw_str and MODE_IMPLIED in op_info_instr:
                addressing_mode = MODE_IMPLIED


            if addressing_mode:
                # Seçilen adresleme modu için opkod bilgilerini al
                mode_specific_op_info = op_info_instr.get(addressing_mode)
                if mode_specific_op_info:
                    return ParsedInstruction(token, mnemonic=mnemonic, addressing_mode=addressing_mode,
                                             operands=final_operands_for_instr, op_info=mode_specific_op_info)
                else:
                    return ParsedInstruction(token, mnemonic=mnemonic,
                                             error=f"Internal error: Mode '{addressing_mode}' not found for '{mnemonic}'.")
            else:
                # Uygun adresleme modu bulunamadı
                expected_modes = ", ".join(op_info_instr.keys())
                return ParsedInstruction(token, mnemonic=mnemonic, op_info=op_info_instr,
                                         error=f"Invalid or missing operands for '{mnemonic}'. Expected modes: {expected_modes}. Got: '{token.operands_raw_str or 'None'}'")

        elif op_info_pseudo: # Bu bir assembler direktifi
            # Direktifler için operand ayrıştırma daha spesifik olabilir
            # Örn: ORG $1000, FCB $10, $20, LABEL EQU $05
            directive_operands = []
            error_msg = None

            if token.operands_raw_str:
                op_parts = [op.strip() for op in self.value_list_regex.split(token.operands_raw_str) if op.strip()]
                if mnemonic == 'EQU' and token.label: # LABEL EQU VALUE
                    if len(op_parts) == 1:
                        val_type, val = self._parse_operand_value(op_parts[0])
                        if val_type not in ['error', 'unknown', 'indexed']: # EQU değeri adres veya sayı olabilir
                            directive_operands.append(val)
                        else:
                            error_msg = f"Invalid value for EQU directive: {op_parts[0]}"
                    else:
                        error_msg = f"EQU directive expects 1 value, got {len(op_parts)}"
                elif mnemonic in ['FCB', 'FDB']:
                    for part in op_parts:
                        val_type, val = self._parse_operand_value(part)
                        # FCB/FDB hem sayı hem de karakter (# 'C') alabilir
                        if val_type.startswith('imm_') or val_type.startswith('address_') or val_type == 'label':
                            directive_operands.append(val) # Değerleri direkt sakla
                        elif val_type == 'error':
                            error_msg = f"Invalid value '{part}' in {mnemonic}: {val}"
                            break
                        else: # 'unknown' veya 'indexed' gibi geçersiz
                            error_msg = f"Invalid value type '{val_type}' for {mnemonic}: {part}"
                            break
                elif mnemonic == 'ORG' or mnemonic == 'RMB':
                    if len(op_parts) == 1:
                        val_type, val = self._parse_operand_value(op_parts[0])
                        if val_type.startswith('address_') or val_type == 'label' or val_type.endswith('_hex') or val_type.endswith('_dec'): # ORG/RMB sayı veya etiket alabilir
                             directive_operands.append(val)
                        elif val_type == 'error':
                            error_msg = f"Invalid value for {mnemonic}: {val}"
                        else:
                            error_msg = f"Invalid value type '{val_type}' for {mnemonic}: {op_parts[0]}"
                    else:
                        error_msg = f"{mnemonic} directive expects 1 argument, got {len(op_parts)}"
                elif mnemonic == 'END':
                    if op_parts: # END normalde operand almaz (opsiyonel başlangıç adresi olabilir ama onu şimdilik desteklemiyoruz)
                        error_msg = "END directive does not take arguments in this implementation."
                else: # Diğer direktifler için genel ayrıştırma
                    for part in op_parts:
                         directive_operands.append(self._parse_operand_value(part)[1]) # Sadece değeri al
            elif mnemonic not in ['END']: # END hariç diğer direktifler operand bekleyebilir
                # ORG, EQU, FCB, FDB, RMB operand bekler
                if op_info_pseudo.get('params', 0) != 0 and op_info_pseudo.get('params') != '1_or_more':
                    error_msg = f"Directive '{mnemonic}' expects operand(s)."


            if error_msg:
                return ParsedInstruction(token, is_directive=True, mnemonic=mnemonic, op_info=op_info_pseudo, error=error_msg)
            else:
                return ParsedInstruction(token, is_directive=True, mnemonic=mnemonic, operands=directive_operands, op_info=op_info_pseudo)

        else: # Ne komut ne de direktif
            return ParsedInstruction(token, error=f"Unknown mnemonic or directive: '{mnemonic}'")


    def parse_tokens(self, token_list):
        """
        Token listesini alır ve ParsedInstruction listesi döndürür.
        """
        parsed_instructions = []
        for token in token_list:
            parsed_instructions.append(self.parse_token(token))
        return parsed_instructions


# Test için örnek kullanım
if __name__ == "__main__":
    from .lexical_analyzer import LexicalAnalyzer # opcode_table'ı import etmeden önce lexer'ı import etmemiz lazım
    # Python'da circular import olmaması için opcode_table'ı doğrudan import etmek yerine
    # bir modül referansı olarak SyntaxAnalyzer'a constructor ile veriyoruz.
    # Bu örnekte, opcode_table.py içindeki fonksiyonları kullanacağız.
    import assembler.opcode_table as ot_module

    lexer = LexicalAnalyzer()
    syntax_analyzer = SyntaxAnalyzer(ot_module)

    sample_code = """
    START EQU $1000
    LOOP: LDAA #$05      ; Load A with 5
          LDAB #%101
          LDX  #150
          ADDA #'$'      ; Add ASCII for $
          ANDA DATA_VAL
          DECA
          BNE  LOOP
          JMP  START
    ADDR1 EQU  $20
          CLR  $30,X     ; Clear memory at $30+X
          LSR  $00F0     ; Logical Shift Right memory
    VALS  FCB  $0A, %00000011, 255, #'Z'
          FDB  $1234, LOOP
          RMB  10
          ORG  $C000
          END
    DATA_VAL EQU $FF
    ERROR_OP LDAA $GG ; Hatalı operand
    NO_SUCH_CMD XYZ #10
    """

    print("--- Parsing Sample Code ---")
    tokens = lexer.tokenize_source_code(sample_code)
    parsed_instrs = syntax_analyzer.parse_tokens(tokens)

    for pi in parsed_instrs:
        print(pi)
        if pi.error:
            print(f"  ERROR on line {pi.token.line_number}: {pi.error}")
        elif not pi.is_directive and pi.op_info:
            print(f"  Opcode Info: Bytes={pi.op_info.get('bytes')}, Opcode=0x{pi.op_info.get('opcode',0):02X}")
        elif pi.is_directive and pi.op_info:
            print(f"  Directive Info: {pi.op_info.get('desc')}") 
