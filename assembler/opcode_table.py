 # m6800_sdk/assembler/opcode_table.py

# Condition Code Register (CCR) Bit Pozisyonları (MSB'den LSB'ye doğru)
# Gerçek M6800'de flag'ler tek bir byte içinde bitler olarak bulunur.
# H I N Z V C
# 1 1 X X X X  (I normalde kullanıcı tarafından doğrudan set/clear edilmez, SWI/RTI ile etkilenir)
# Bu bit pozisyonları, CCR byte'ındaki bit indeksleri olarak düşünülebilir (örn: 0'dan 5'e veya 7'ye).
# Şimdilik sembolik sabitler olarak tanımlayalım, simülatörde gerçek bitlere map ederiz.

# Örnek flag tanımlamaları (Simülatörde gerçek CCR byte'ı ile uyumlu olmalı)
# Bit 5: H (Half-carry)
# Bit 4: I (Interrupt mask) - Genellikle doğrudan etkilenmez, SWI/RTI ile değişir
# Bit 3: N (Negative)
# Bit 2: Z (Zero)
# Bit 1: V (Overflow)
# Bit 0: C (Carry/Borrow)

FLAG_H = 'H'
FLAG_I = 'I' # Genellikle kullanıcı komutlarıyla doğrudan değişmez
FLAG_N = 'N'
FLAG_Z = 'Z'
FLAG_V = 'V'
FLAG_C = 'C'

# Adresleme Modları için sabitler
MODE_IMPLIED = "IMPLIED"
MODE_IMMEDIATE = "IMMED"
MODE_DIRECT = "DIRECT"
MODE_EXTENDED = "EXTND"
MODE_INDEXED = "INDEX"
MODE_RELATIVE = "REL" # Branch komutları için

# Her komut için:
# 'mnemonic': {
#     MODE_XXX: {'opcode': 0xYY, 'bytes': N, 'cycles': M,
#                'flags_affected': [FLAG_N, FLAG_Z, ...],
#                'flags_logic': {'N': 'result < 0', 'Z': 'result == 0', ...} # Opsiyonel, flag'lerin nasıl set edileceğine dair mantık
#                'description': "Kısa açıklama"},
#     ...
# }
# 'cycles' şimdilik opsiyonel, simülasyonun doğruluğu için eklenebilir.
# 'flags_logic' hangi koşulda hangi flag'in set olacağını belirtir.
# Bazı komutlar flag'leri belirli bir değere set eder (örn: V=0). Bunları da belirtebiliriz.

INSTRUCTION_SET = {
    # --- TABLE 2: ACCUMULATOR AND MEMORY OPERATIONS ---
    'ABA': {
        MODE_IMPLIED: {'opcode': 0x1B, 'bytes': 1, 'flags_affected': [FLAG_H, FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add Accumulators"},
    },
    'ADCA': {
        MODE_IMMEDIATE: {'opcode': 0x89, 'bytes': 2, 'flags_affected': [FLAG_H, FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add with Carry to A"},
        MODE_DIRECT:    {'opcode': 0x99, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add with Carry to A"}, # H not affected in direct for ADCA/SBCA as per some docs
        MODE_INDEXED:   {'opcode': 0xA9, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add with Carry to A"},
        MODE_EXTENDED:  {'opcode': 0xB9, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add with Carry to A"},
    },
    'ADCB': {
        MODE_IMMEDIATE: {'opcode': 0xC9, 'bytes': 2, 'flags_affected': [FLAG_H, FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add with Carry to B"},
        MODE_DIRECT:    {'opcode': 0xD9, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add with Carry to B"},
        MODE_INDEXED:   {'opcode': 0xE9, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add with Carry to B"},
        MODE_EXTENDED:  {'opcode': 0xF9, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add with Carry to B"},
    },
    'ADDA': {
        MODE_IMMEDIATE: {'opcode': 0x8B, 'bytes': 2, 'flags_affected': [FLAG_H, FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add to A"},
        MODE_DIRECT:    {'opcode': 0x9B, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add to A"},
        MODE_INDEXED:   {'opcode': 0xAB, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add to A"},
        MODE_EXTENDED:  {'opcode': 0xBB, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add to A"},
    },
    'ADDB': {
        MODE_IMMEDIATE: {'opcode': 0xCB, 'bytes': 2, 'flags_affected': [FLAG_H, FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add to B"},
        MODE_DIRECT:    {'opcode': 0xDB, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add to B"},
        MODE_INDEXED:   {'opcode': 0xEB, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add to B"},
        MODE_EXTENDED:  {'opcode': 0xFB, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Add to B"},
    },
    'ANDA': {
        MODE_IMMEDIATE: {'opcode': 0x84, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "AND with A"}, # V is cleared
        MODE_DIRECT:    {'opcode': 0x94, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "AND with A"},
        MODE_INDEXED:   {'opcode': 0xA4, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "AND with A"},
        MODE_EXTENDED:  {'opcode': 0xB4, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "AND with A"},
    },
    'ANDB': {
        MODE_IMMEDIATE: {'opcode': 0xC4, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "AND with B"}, # V is cleared
        MODE_DIRECT:    {'opcode': 0xD4, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "AND with B"},
        MODE_INDEXED:   {'opcode': 0xE4, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "AND with B"},
        MODE_EXTENDED:  {'opcode': 0xF4, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "AND with B"},
    },
    'ASL': { # Arithmetic Shift Left (Memory)
        MODE_INDEXED:   {'opcode': 0x68, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Arithmetic Shift Left Memory"}, # Yanlış opkod, 78 olmalı
        MODE_EXTENDED:  {'opcode': 0x78, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Arithmetic Shift Left Memory"},
    },
    'ASLA': {
        MODE_IMPLIED:   {'opcode': 0x48, 'bytes': 1, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Arithmetic Shift Left A"},
    },
    'ASLB': {
        MODE_IMPLIED:   {'opcode': 0x58, 'bytes': 1, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Arithmetic Shift Left B"},
    },
    'ASR': { # Arithmetic Shift Right (Memory)
        MODE_INDEXED:   {'opcode': 0x67, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_C], 'desc': "Arithmetic Shift Right Memory"}, # Yanlış opkod, 77 olmalı
        MODE_EXTENDED:  {'opcode': 0x77, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_C], 'desc': "Arithmetic Shift Right Memory"},
    },
    'ASRA': {
        MODE_IMPLIED:   {'opcode': 0x47, 'bytes': 1, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_C], 'desc': "Arithmetic Shift Right A"},
    },
    'ASRB': {
        MODE_IMPLIED:   {'opcode': 0x57, 'bytes': 1, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_C], 'desc': "Arithmetic Shift Right B"},
    },
    # ... (Diğer tüm komutlar bu şekilde eklenecek) ...
    # Örnek bir branch komutu
    'BCC': {
        MODE_RELATIVE:  {'opcode': 0x24, 'bytes': 2, 'flags_affected': [], 'condition_true': lambda ccr: not ccr.C, 'desc': "Branch if Carry Clear"},
    },
    'BCS': {
        MODE_RELATIVE:  {'opcode': 0x25, 'bytes': 2, 'flags_affected': [], 'condition_true': lambda ccr: ccr.C, 'desc': "Branch if Carry Set"},
    },
    'BEQ': {
        MODE_RELATIVE:  {'opcode': 0x27, 'bytes': 2, 'flags_affected': [], 'condition_true': lambda ccr: ccr.Z, 'desc': "Branch if Equal (Z=1)"},
    },
    # ... Diğer branch komutları ...
    'BRA': {
        MODE_RELATIVE:  {'opcode': 0x20, 'bytes': 2, 'flags_affected': [], 'condition_true': lambda ccr: True, 'desc': "Branch Always"},
    },
    # ...
    'LDAA': {
        MODE_IMMEDIATE: {'opcode': 0x86, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Accumulator A"},
        MODE_DIRECT:    {'opcode': 0x96, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Accumulator A"},
        MODE_INDEXED:   {'opcode': 0xA6, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Accumulator A"},
        MODE_EXTENDED:  {'opcode': 0xB6, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Accumulator A"},
    },
    'LDAB': {
        MODE_IMMEDIATE: {'opcode': 0xC6, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Accumulator B"},
        MODE_DIRECT:    {'opcode': 0xD6, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Accumulator B"},
        MODE_INDEXED:   {'opcode': 0xE6, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Accumulator B"},
        MODE_EXTENDED:  {'opcode': 0xF6, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Accumulator B"},
    },
    # ...
    'STAA': {
        MODE_DIRECT:    {'opcode': 0x97, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Accumulator A"},
        MODE_INDEXED:   {'opcode': 0xA7, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Accumulator A"},
        MODE_EXTENDED:  {'opcode': 0xB7, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Accumulator A"},
    },
    'STAB': {
        MODE_DIRECT:    {'opcode': 0xD7, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Accumulator B"}, # D7 olmalı, C7 değil
        MODE_INDEXED:   {'opcode': 0xE7, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Accumulator B"},
        MODE_EXTENDED:  {'opcode': 0xF7, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Accumulator B"},
    },
    # --- TABLE 3: INDEX REGISTER AND STACK POINTER INSTRUCTIONS ---
    'CPX': {
        MODE_IMMEDIATE: {'opcode': 0x8C, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V], 'desc': "Compare Index Register"},
        MODE_DIRECT:    {'opcode': 0x9C, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V], 'desc': "Compare Index Register"},
        MODE_INDEXED:   {'opcode': 0xAC, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V], 'desc': "Compare Index Register"},
        MODE_EXTENDED:  {'opcode': 0xBC, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V], 'desc': "Compare Index Register"},
    },
    'DEX': {
        MODE_IMPLIED:   {'opcode': 0x09, 'bytes': 1, 'flags_affected': [FLAG_Z], 'desc': "Decrement Index Register"}, # 09 olmalı, 08 değil
    },
    'DES': {
        MODE_IMPLIED:   {'opcode': 0x34, 'bytes': 1, 'flags_affected': [], 'desc': "Decrement Stack Pointer"},
    },
    'INX': {
        MODE_IMPLIED:   {'opcode': 0x08, 'bytes': 1, 'flags_affected': [FLAG_Z], 'desc': "Increment Index Register"},
    },
    'INS': {
        MODE_IMPLIED:   {'opcode': 0x31, 'bytes': 1, 'flags_affected': [], 'desc': "Increment Stack Pointer"},
    },
    'LDX': {
        MODE_IMMEDIATE: {'opcode': 0xCE, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Index Register"},
        MODE_DIRECT:    {'opcode': 0xDE, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Index Register"},
        MODE_INDEXED:   {'opcode': 0xEE, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Index Register"},
        MODE_EXTENDED:  {'opcode': 0xFE, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Index Register"},
    },
    'LDS': {
        MODE_IMMEDIATE: {'opcode': 0x8E, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Stack Pointer"},
        MODE_DIRECT:    {'opcode': 0x9E, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Stack Pointer"}, # 9E olmalı, 95 değil
        MODE_INDEXED:   {'opcode': 0xAE, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Stack Pointer"},
        MODE_EXTENDED:  {'opcode': 0xBE, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Load Stack Pointer"},
    },
    'STX': {
        MODE_DIRECT:    {'opcode': 0xDF, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Index Register"}, # DF olmalı, OF değil
        MODE_INDEXED:   {'opcode': 0xEF, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Index Register"},
        MODE_EXTENDED:  {'opcode': 0xFF, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Index Register"},
    },
    'STS': {
        MODE_DIRECT:    {'opcode': 0x9F, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Stack Pointer"},
        MODE_INDEXED:   {'opcode': 0xAF, 'bytes': 2, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Stack Pointer"},
        MODE_EXTENDED:  {'opcode': 0xBF, 'bytes': 3, 'flags_affected': [FLAG_N, FLAG_Z], 'v_flag_clear': True, 'desc': "Store Stack Pointer"},
    },
    'TXS': {
        MODE_IMPLIED:   {'opcode': 0x35, 'bytes': 1, 'flags_affected': [], 'desc': "Transfer Index Reg to Stack Pntr"},
    },
    'TSX': {
        MODE_IMPLIED:   {'opcode': 0x30, 'bytes': 1, 'flags_affected': [], 'desc': "Transfer Stack Pntr to Index Reg"},
    },

    # --- TABLE 4: JUMP AND BRANCH INSTRUCTIONS ---
    'JMP': {
        MODE_INDEXED:   {'opcode': 0x6E, 'bytes': 2, 'flags_affected': [], 'desc': "Jump"},
        MODE_EXTENDED:  {'opcode': 0x7E, 'bytes': 3, 'flags_affected': [], 'desc': "Jump"},
    },
    'JSR': {
        MODE_INDEXED:   {'opcode': 0xAD, 'bytes': 2, 'flags_affected': [], 'desc': "Jump to Subroutine"},
        MODE_EXTENDED:  {'opcode': 0xBD, 'bytes': 3, 'flags_affected': [], 'desc': "Jump to Subroutine"},
    },
    'NOP': {
        MODE_IMPLIED:   {'opcode': 0x01, 'bytes': 1, 'flags_affected': [], 'desc': "No Operation"},
    },
    'RTI': {
        MODE_IMPLIED:   {'opcode': 0x3B, 'bytes': 1, 'flags_affected': [FLAG_H, FLAG_I, FLAG_N, FLAG_Z, FLAG_V, FLAG_C], 'desc': "Return from Interrupt"}, # Tüm flag'ler yığından çekilir
    },
    'RTS': {
        MODE_IMPLIED:   {'opcode': 0x39, 'bytes': 1, 'flags_affected': [], 'desc': "Return from Subroutine"},
    },
    'SWI': {
        MODE_IMPLIED:   {'opcode': 0x3F, 'bytes': 1, 'flags_affected': [FLAG_I], 'i_flag_set': True, 'desc': "Software Interrupt"}, # I flag'i set edilir
    },
    'WAI': {
        MODE_IMPLIED:   {'opcode': 0x3E, 'bytes': 1, 'flags_affected': [], 'desc': "Wait for Interrupt"}, # Aslında I flag'ini etkiler (interrupt beklerken)
    },
    # Diğer tüm komutlar benzer şekilde doldurulacak...
    'INCA': {
    MODE_IMPLIED: {'opcode': 0x4C, 'bytes': 1, 'cycles': 2, 'flags_affected': [FLAG_N, FLAG_Z, FLAG_V], 'desc': "Increment Accumulator A"},
    },
     'DECB': {
        MODE_IMPLIED: {
            'opcode': 0x5A, 
            'bytes': 1,
            'cycles': 2,
            'flags_affected': [FLAG_N, FLAG_Z, FLAG_V],
            'desc': "Decrement Accumulator B"
        }
    },
}

# Pseudo-işlemler (Assembler direktifleri)
PSEUDO_OPS = {
    'ORG': {'params': 1, 'type': 'address', 'desc': "Set program origin"},
    'END': {'params': 0, 'desc': "End of program"},
    'EQU': {'params': 1, 'type': 'value', 'desc': "Equate symbol to value"}, # Label EQU Value
    'FCB': {'params': '1_or_more', 'type': 'byte_values', 'desc': "Form Constant Byte(s)"}, # BYTE
    'FDB': {'params': '1_or_more', 'type': 'word_values', 'desc': "Form Double Byte(s) / Form Constant Word"}, # WORD
    'RMB': {'params': 1, 'type': 'count', 'desc': "Reserve Memory Bytes"}, # RESB
    # Diğer pseudo op'lar eklenebilir (örn: FCC - Form Constant Character string)
}

def get_instruction_info(mnemonic):
    """Verilen mnemonik için instruction setten bilgileri alır."""
    return INSTRUCTION_SET.get(mnemonic.upper())

def get_pseudo_op_info(directive):
    """Verilen assembler direktifi için bilgileri alır."""
    return PSEUDO_OPS.get(directive.upper())

# Test için örnek kullanım (bu dosya doğrudan çalıştırıldığında)
if __name__ == "__main__":
    print("LDAA IMMED Opcode:", INSTRUCTION_SET['LDAA'][MODE_IMMEDIATE]['opcode'])
    print("ORG params:", PSEUDO_OPS['ORG']['params'])
    print("BCC condition:", INSTRUCTION_SET['BCC'][MODE_RELATIVE]['desc'])
    if INSTRUCTION_SET['BCC'][MODE_RELATIVE]['condition_true']({'C': False}): # Örnek CCR durumu
         print("BCC would branch if C=0")
