from .cpu import CPU, CCR
from assembler.opcode_table import (
    FLAG_H, FLAG_I, FLAG_N, FLAG_Z, FLAG_V, FLAG_C,
    INSTRUCTION_SET, # Artık tüm instruction setini alıyoruz
    MODE_IMPLIED, MODE_IMMEDIATE, MODE_DIRECT,
    MODE_EXTENDED, MODE_INDEXED, MODE_RELATIVE
)

class InstructionExecutor:
    def __init__(self, cpu: CPU, opcode_table_module): # opcode_table_module artık kullanılmıyor, direkt INSTRUCTION_SET'i alıyoruz
        self.cpu = cpu
        # self.opcode_table = opcode_table_module # Yerine direkt INSTRUCTION_SET kullanılacak
        self.op_info = None
        self.current_opcode_byte = 0
        self.dispatch_table = self._build_dispatch_table()

    def _build_dispatch_table(self):
        table = {}
        # Her mnemonic ve modu için handler'ı direkt opkoda map et
        for mnemonic_upper, modes_dict in INSTRUCTION_SET.items():
            handler_method_name = f"_execute_{mnemonic_upper.lower()}"
            if hasattr(self, handler_method_name):
                handler_func_for_mnemonic = getattr(self, handler_method_name)
                for mode, details in modes_dict.items():
                    opcode_val = details.get('opcode')
                    if opcode_val is not None:
                        if opcode_val not in table:
                            table[opcode_val] = handler_func_for_mnemonic
                        # else:
                            # print(f"Warning: Opcode {opcode_val:02X} already has a handler. Mnemonic: {mnemonic_upper}, Mode: {mode}")
            # else:
                # print(f"Warning: No handler method found for mnemonic {mnemonic_upper} ({handler_method_name})")
        return table

    def _fetch_operand_byte(self):
        val = self.cpu.memory.read_byte(self.cpu.PC)
        self.cpu.PC = (self.cpu.PC + 1) & 0xFFFF
        return val

    def _fetch_operand_word(self):
        high_byte = self._fetch_operand_byte()
        low_byte = self._fetch_operand_byte()
        return (high_byte << 8) | low_byte

    def _get_effective_address(self, mode): # op_info'ya gerek yok, mode yeterli
        eff_addr = 0
        if mode == MODE_DIRECT:
            eff_addr = self._fetch_operand_byte()
        elif mode == MODE_EXTENDED:
            eff_addr = self._fetch_operand_word()
        elif mode == MODE_INDEXED:
            offset = self._fetch_operand_byte()
            eff_addr = (self.cpu.X + offset) & 0xFFFF
        return eff_addr

    def execute_next_instruction(self):
        if self.cpu.is_halted:
            return 0

        start_pc = self.cpu.PC
        try:
            self.current_opcode_byte = self._fetch_operand_byte()
        except ValueError as e:
            print(f"Halt: Error fetching opcode at ${start_pc:04X}. {e}")
            self.cpu.is_halted = True
            return 0

        handler_func = self.dispatch_table.get(self.current_opcode_byte)

        if handler_func:
            mnemonic_found = None
            mode_found = None
            self.op_info = None

            for mnem, modes_dict in INSTRUCTION_SET.items():
                for mode, details in modes_dict.items():
                    if details.get('opcode') == self.current_opcode_byte:
                        mnemonic_found = mnem
                        mode_found = mode
                        self.op_info = details
                        break
                if mnemonic_found:
                    break

            if not self.op_info:
                print(f"Halt: Opcode ${self.current_opcode_byte:02X} at ${start_pc:04X} has no op_info in table.")
                self.cpu.is_halted = True
                return 0
            try:
                # print(f"PC:${start_pc:04X} Op:${self.current_opcode_byte:02X} ({mnemonic_found} {mode_found}) A:{self.cpu.A:02X} B:{self.cpu.B:02X} X:{self.cpu.X:04X} SP:{self.cpu.SP:04X} CCR:{self.cpu.CCR}")
                handler_func(mode_found)
                cycles = self.op_info.get('cycles', 1)
                self.cpu.cycles_executed += cycles
                return cycles
            except ValueError as e:
                 print(f"Halt: Runtime error during {mnemonic_found} at ${start_pc:04X}. {e}")
                 self.cpu.is_halted = True
                 return 0
            except Exception as e:
                 print(f"Halt: Unexpected error during {mnemonic_found} at ${start_pc:04X}. {e}")
                 import traceback
                 traceback.print_exc()
                 self.cpu.is_halted = True
                 return 0
        else:
            print(f"Halt: Unknown opcode ${self.current_opcode_byte:02X} encountered at PC=${start_pc:04X}.")
            self.cpu.is_halted = True
            return 0

    # --- Helper for arithmetic flags ---
    def _set_flags_add_sub(self, acc_val_before, operand, result_8bit, is_sub=False, with_carry=False, carry_in=False):
        # H (Half Carry/Borrow)
        if is_sub:
            # H = (A_lo < M_lo) if no borrow_in, or (A_lo <= M_lo) if borrow_in (for nibble)
            # H = (A_n3 / M_n3 / R_n3) + (A_n3 * /M_n3 * /R_n3) (classic subtract borrow)
            # More simply: A_lo - M_lo - C_in_nibble < 0
            a_lo = acc_val_before & 0x0F
            m_lo = operand & 0x0F
            c_in_nibble = (carry_in if with_carry else False) # For SBC, carry_in is from bit 7 of previous operation. For half-carry, it's complex.
                                                            # M6800 H flag for subtract is (A3' M3' R3) + (A3 M3 R3')
                                                            # For now, simplified:
            self.cpu.CCR.H = bool((a_lo - m_lo - (1 if (with_carry and carry_in and is_sub) else 0)) < 0) # Approximat

        else: # Add
            self.cpu.CCR.H = bool(((acc_val_before & 0x0F) + (operand & 0x0F) + (1 if (with_carry and carry_in) else 0)) > 0x0F)

        # N, Z
        self.cpu.set_nz_flags(result_8bit)

        # V (Overflow)
        # For add: V = A7 M7 R7' + A7' M7' R7
        # For sub: V = A7 M7' R7' + A7' M7 R7  (M is effectively 2's complement)
        a7 = bool(acc_val_before & 0x80)
        m7 = bool(operand & 0x80)
        r7 = bool(result_8bit & 0x80)
        if is_sub:
            self.cpu.CCR.V = (a7 and not m7 and not r7) or (not a7 and m7 and r7)
        else: # Add
            self.cpu.CCR.V = (a7 and m7 and not r7) or (not a7 and not m7 and r7)

        # C (Carry/Borrow)
        # For add: C = A7 M7 + M7 R7' + R7' A7
        # More simply: C = (A + M + C_in) > 0xFF
        # For sub: C = A7' M7 + M7 R7 + R7 A7' (Borrow, so C=1 if borrow occurs)
        # More simply: C = (A - M - C_in) < 0
        if is_sub:
            self.cpu.CCR.C = bool((acc_val_before - operand - (1 if (with_carry and carry_in) else 0)) < 0)
        else: # Add
            self.cpu.CCR.C = bool((acc_val_before + operand + (1 if (with_carry and carry_in) else 0)) > 0xFF)


    # --- Accumulator and Memory Operations (TABLE 2) ---
    def _execute_aba(self, mode): # Add B to A
        a_old = self.cpu.A
        b_val = self.cpu.B
        res16 = a_old + b_val
        self.cpu.A = res16 & 0xFF
        self._set_flags_add_sub(a_old, b_val, self.cpu.A)

    def _execute_adca(self, mode): # Add with Carry to A
        a_old = self.cpu.A
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        carry_in = self.cpu.CCR.C
        res16 = a_old + mem_val + (1 if carry_in else 0)
        self.cpu.A = res16 & 0xFF
        self._set_flags_add_sub(a_old, mem_val, self.cpu.A, with_carry=True, carry_in=carry_in)

    def _execute_adcb(self, mode): # Add with Carry to B
        b_old = self.cpu.B
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        carry_in = self.cpu.CCR.C
        res16 = b_old + mem_val + (1 if carry_in else 0)
        self.cpu.B = res16 & 0xFF
        self._set_flags_add_sub(b_old, mem_val, self.cpu.B, with_carry=True, carry_in=carry_in)

    def _execute_adda(self, mode): # Add to A
        a_old = self.cpu.A
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        res16 = a_old + mem_val
        self.cpu.A = res16 & 0xFF
        self._set_flags_add_sub(a_old, mem_val, self.cpu.A)

    def _execute_addb(self, mode): # Add to B
        b_old = self.cpu.B
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        res16 = b_old + mem_val
        self.cpu.B = res16 & 0xFF
        self._set_flags_add_sub(b_old, mem_val, self.cpu.B)

    def _execute_anda(self, mode): # Logical AND A
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        self.cpu.A &= mem_val
        self.cpu.set_nz_flags(self.cpu.A)
        self.cpu.CCR.V = False

    def _execute_andb(self, mode): # Logical AND B
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        self.cpu.B &= mem_val
        self.cpu.set_nz_flags(self.cpu.B)
        self.cpu.CCR.V = False

    def _execute_asl(self, mode): # Arithmetic Shift Left (Memory)
        eff_addr = self._get_effective_address(mode)
        val = self.cpu.memory.read_byte(eff_addr)
        self.cpu.CCR.C = bool(val & 0x80) # Bit 7 goes to Carry
        val = (val << 1) & 0xFF
        self.cpu.memory.write_byte(eff_addr, val)
        self.cpu.set_nz_flags(val)
        self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C # V = N xor C

    def _execute_asla(self, mode): # Arithmetic Shift Left A
        self.cpu.CCR.C = bool(self.cpu.A & 0x80)
        self.cpu.A = (self.cpu.A << 1) & 0xFF
        self.cpu.set_nz_flags(self.cpu.A)
        self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C

    def _execute_aslb(self, mode): # Arithmetic Shift Left B
        self.cpu.CCR.C = bool(self.cpu.B & 0x80)
        self.cpu.B = (self.cpu.B << 1) & 0xFF
        self.cpu.set_nz_flags(self.cpu.B)
        self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C

    def _execute_asr(self, mode): # Arithmetic Shift Right (Memory)
        eff_addr = self._get_effective_address(mode)
        val = self.cpu.memory.read_byte(eff_addr)
        self.cpu.CCR.C = bool(val & 0x01) # Bit 0 goes to Carry
        msb = val & 0x80 # Keep MSB
        val = (val >> 1) | msb
        self.cpu.memory.write_byte(eff_addr, val)
        self.cpu.set_nz_flags(val)
        self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C # V = N xor C (ASR V logic)

    def _execute_asra(self, mode): # Arithmetic Shift Right A
        self.cpu.CCR.C = bool(self.cpu.A & 0x01)
        msb = self.cpu.A & 0x80
        self.cpu.A = (self.cpu.A >> 1) | msb
        self.cpu.set_nz_flags(self.cpu.A)
        self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C

    def _execute_asrb(self, mode): # Arithmetic Shift Right B
        self.cpu.CCR.C = bool(self.cpu.B & 0x01)
        msb = self.cpu.B & 0x80
        self.cpu.B = (self.cpu.B >> 1) | msb
        self.cpu.set_nz_flags(self.cpu.B)
        self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C

    # Branch instructions already defined in the previous response
    def _branch_if_condition(self, condition_true):
        rel_offset_signed_byte = self._fetch_operand_byte()
        offset_val = rel_offset_signed_byte
        if rel_offset_signed_byte & 0x80: # Negative
            offset_val = rel_offset_signed_byte - 256
        if condition_true:
            self.cpu.PC = (self.cpu.PC + offset_val) & 0xFFFF

    def _execute_bcc(self, mode): self._branch_if_condition(not self.cpu.CCR.C)
    def _execute_bcs(self, mode): self._branch_if_condition(self.cpu.CCR.C)
    def _execute_beq(self, mode): self._branch_if_condition(self.cpu.CCR.Z)
    def _execute_bge(self, mode): self._branch_if_condition(not (self.cpu.CCR.N ^ self.cpu.CCR.V)) # N XOR V = 0
    def _execute_bgt(self, mode): self._branch_if_condition(not (self.cpu.CCR.Z or (self.cpu.CCR.N ^ self.cpu.CCR.V))) # Z OR (N XOR V) = 0
    def _execute_bhi(self, mode): self._branch_if_condition(not (self.cpu.CCR.C or self.cpu.CCR.Z)) # C OR Z = 0
    def _execute_ble(self, mode): self._branch_if_condition(self.cpu.CCR.Z or (self.cpu.CCR.N ^ self.cpu.CCR.V)) # Z OR (N XOR V) = 1
    def _execute_bls(self, mode): self._branch_if_condition(self.cpu.CCR.C or self.cpu.CCR.Z) # C OR Z = 1
    def _execute_blt(self, mode): self._branch_if_condition(self.cpu.CCR.N ^ self.cpu.CCR.V) # N XOR V = 1
    def _execute_bmi(self, mode): self._branch_if_condition(self.cpu.CCR.N)
    def _execute_bne(self, mode): self._branch_if_condition(not self.cpu.CCR.Z)
    def _execute_bpl(self, mode): self._branch_if_condition(not self.cpu.CCR.N)
    def _execute_bra(self, mode): self._branch_if_condition(True)
    def _execute_bsr(self, mode): # Branch to Subroutine
        rel_offset_signed_byte = self._fetch_operand_byte()
        offset_val = rel_offset_signed_byte
        if rel_offset_signed_byte & 0x80: offset_val -= 256
        # Push current PC (which is address of next instruction AFTER BSR's operand)
        self.cpu.push_word_to_stack(self.cpu.PC)
        self.cpu.PC = (self.cpu.PC + offset_val) & 0xFFFF

    def _execute_bvc(self, mode): self._branch_if_condition(not self.cpu.CCR.V)
    def _execute_bvs(self, mode): self._branch_if_condition(self.cpu.CCR.V)

    def _execute_bita(self, mode): # Bit Test A
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        res = self.cpu.A & mem_val
        self.cpu.set_nz_flags(res)
        self.cpu.CCR.V = False

    def _execute_bitb(self, mode): # Bit Test B
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        res = self.cpu.B & mem_val
        self.cpu.set_nz_flags(res)
        self.cpu.CCR.V = False

    def _execute_cba(self, mode): # Compare Accumulators (A - B)
        a_val = self.cpu.A
        b_val = self.cpu.B
        res16 = a_val - b_val # For carry and overflow
        res8 = res16 & 0xFF
        self.cpu.set_nz_flags(res8)
        # V = A7 B7' R7' + A7' B7 R7
        a7 = bool(a_val & 0x80); b7 = bool(b_val & 0x80); r7 = bool(res8 & 0x80)
        self.cpu.CCR.V = (a7 and not b7 and not r7) or (not a7 and b7 and r7)
        self.cpu.CCR.C = bool(res16 < 0) # C is set if A < B (borrow occurred)

    def _execute_clc(self, mode): self.cpu.CCR.C = False
    def _execute_cli(self, mode): self.cpu.CCR.I = False
    def _execute_clr(self, mode): # Clear Memory
        eff_addr = self._get_effective_address(mode)
        self.cpu.memory.write_byte(eff_addr, 0)
        self.cpu.CCR.N = False; self.cpu.CCR.Z = True; self.cpu.CCR.V = False; self.cpu.CCR.C = False

    def _execute_clra(self, mode): self.cpu.A = 0; self.cpu.CCR.N = False; self.cpu.CCR.Z = True; self.cpu.CCR.V = False; self.cpu.CCR.C = False
    def _execute_clrb(self, mode): self.cpu.B = 0; self.cpu.CCR.N = False; self.cpu.CCR.Z = True; self.cpu.CCR.V = False; self.cpu.CCR.C = False
    def _execute_clv(self, mode): self.cpu.CCR.V = False

    def _execute_cmpa(self, mode): # Compare A with Memory (A - M)
        a_val = self.cpu.A
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        res16 = a_val - mem_val
        res8 = res16 & 0xFF
        self.cpu.set_nz_flags(res8)
        a7 = bool(a_val & 0x80); m7 = bool(mem_val & 0x80); r7 = bool(res8 & 0x80)
        self.cpu.CCR.V = (a7 and not m7 and not r7) or (not a7 and m7 and r7)
        self.cpu.CCR.C = bool(res16 < 0)

    def _execute_cmpb(self, mode): # Compare B with Memory (B - M)
        b_val = self.cpu.B
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        res16 = b_val - mem_val
        res8 = res16 & 0xFF
        self.cpu.set_nz_flags(res8)
        b7 = bool(b_val & 0x80); m7 = bool(mem_val & 0x80); r7 = bool(res8 & 0x80)
        self.cpu.CCR.V = (b7 and not m7 and not r7) or (not b7 and m7 and r7)
        self.cpu.CCR.C = bool(res16 < 0)

    def _execute_com(self, mode): # Complement Memory (1's Complement)
        eff_addr = self._get_effective_address(mode)
        val = self.cpu.memory.read_byte(eff_addr)
        val = ~val & 0xFF
        self.cpu.memory.write_byte(eff_addr, val)
        self.cpu.set_nz_flags(val)
        self.cpu.CCR.V = False; self.cpu.CCR.C = True # COM always sets C

    def _execute_coma(self, mode): self.cpu.A = ~self.cpu.A & 0xFF; self.cpu.set_nz_flags(self.cpu.A); self.cpu.CCR.V = False; self.cpu.CCR.C = True
    def _execute_comb(self, mode): self.cpu.B = ~self.cpu.B & 0xFF; self.cpu.set_nz_flags(self.cpu.B); self.cpu.CCR.V = False; self.cpu.CCR.C = True

    def _execute_cpx(self, mode): # Compare Index Register (X - M:M+1)
        x_val = self.cpu.X
        mem_val = 0
        if mode == MODE_IMMEDIATE: mem_val = self._fetch_operand_word()
        else: mem_val = self.cpu.memory.read_word(self._get_effective_address(mode))
        # CPX uses 16-bit subtraction for N, Z, V. C is not affected.
        res32 = x_val - mem_val # For potential borrow out of 16 bits
        res16 = res32 & 0xFFFF
        self.cpu.set_nz_flags_16bit(res16)
        # V = X15 M15' R15' + X15' M15 R15
        x15 = bool(x_val & 0x8000); m15 = bool(mem_val & 0x8000); r15 = bool(res16 & 0x8000)
        self.cpu.CCR.V = (x15 and not m15 and not r15) or (not x15 and m15 and r15)
        # C is NOT affected by CPX

    def _execute_daa(self, mode): # Decimal Adjust Accumulator A
        # Converts binary sum of two BCD numbers in A into BCD format
        a_val = self.cpu.A
        correction = 0
        c_flag_before = self.cpu.CCR.C
        h_flag_before = self.cpu.CCR.H # DAA uses H flag from previous ADD/ADC

        # If low nibble > 9 or H flag was set
        if (a_val & 0x0F) > 0x09 or h_flag_before:
            correction |= 0x06
        # If high nibble > 9 or C flag was set (or after low nibble correction, high nibble becomes > 9)
        # The condition (a_val > 0x99) should use a_val before low nibble correction for upper check
        if a_val > 0x99 or c_flag_before:
            correction |= 0x60
            self.cpu.CCR.C = True # Set C if correction $60 is needed
        else:
            self.cpu.CCR.C = False # Clear C if no high nibble adjustment for carry

        # A second check for high nibble after low nibble correction
        # (If A_hi + (A_lo_carry_from_06) > 9)
        # This is complex, let's simplify: if a_val + correction would set carry or high nibble > 9
        # A simpler way: (a_val & 0xF0) after adding (correction&0x0F) is checked with the high nibble correction
        temp_a = a_val + (correction & 0x0F) # Apply low nibble correction first for checking high nibble
        if (temp_a & 0xF0) > 0x90 and (correction & 0x60) == 0: # If high became >9 due to low correction and no high corr. yet
            if not c_flag_before: # If original C was not set, but now it needs to be
                 correction |= 0x60
                 self.cpu.CCR.C = True


        self.cpu.A = (a_val + correction) & 0xFF
        self.cpu.set_nz_flags(self.cpu.A)
        # V is undefined after DAA. Some emulators leave it, some clear it.
        # Motorola docs say "not affected" or "undefined". Let's leave it as is.

    def _execute_dec(self, mode): # Decrement Memory
        eff_addr = self._get_effective_address(mode)
        val = self.cpu.memory.read_byte(eff_addr)
        val_old = val
        val = (val - 1) & 0xFF
        self.cpu.memory.write_byte(eff_addr, val)
        self.cpu.set_nz_flags(val)
        self.cpu.CCR.V = (val == 0x7F and val_old == 0x80) # Set if M was $80

    def _execute_deca(self, mode): self.cpu.A = (self.cpu.A - 1) & 0xFF; self.cpu.set_nz_flags(self.cpu.A); self.cpu.CCR.V = (self.cpu.A == 0x7F)
    def _execute_decb(self, mode): self.cpu.B = (self.cpu.B - 1) & 0xFF; self.cpu.set_nz_flags(self.cpu.B); self.cpu.CCR.V = (self.cpu.B == 0x7F)
    def _execute_des(self, mode): self.cpu.SP = (self.cpu.SP - 1) & 0xFFFF # No flags affected
    def _execute_dex(self, mode): self.cpu.X = (self.cpu.X - 1) & 0xFFFF; self.cpu.CCR.Z = (self.cpu.X == 0) # Only Z affected

    def _execute_eora(self, mode): # Exclusive OR A
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        self.cpu.A ^= mem_val
        self.cpu.set_nz_flags(self.cpu.A)
        self.cpu.CCR.V = False

    def _execute_eorb(self, mode): # Exclusive OR B
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        self.cpu.B ^= mem_val
        self.cpu.set_nz_flags(self.cpu.B)
        self.cpu.CCR.V = False

    def _execute_inc(self, mode): # Increment Memory
        eff_addr = self._get_effective_address(mode)
        val = self.cpu.memory.read_byte(eff_addr)
        val_old = val
        val = (val + 1) & 0xFF
        self.cpu.memory.write_byte(eff_addr, val)
        self.cpu.set_nz_flags(val)
        self.cpu.CCR.V = (val == 0x80 and val_old == 0x7F) # Set if M was $7F

    def _execute_inca(self, mode): self.cpu.A = (self.cpu.A + 1) & 0xFF; self.cpu.set_nz_flags(self.cpu.A); self.cpu.CCR.V = (self.cpu.A == 0x80)
    def _execute_incb(self, mode): self.cpu.B = (self.cpu.B + 1) & 0xFF; self.cpu.set_nz_flags(self.cpu.B); self.cpu.CCR.V = (self.cpu.B == 0x80)
    def _execute_ins(self, mode): self.cpu.SP = (self.cpu.SP + 1) & 0xFFFF # No flags affected
    def _execute_inx(self, mode): self.cpu.X = (self.cpu.X + 1) & 0xFFFF; self.cpu.CCR.Z = (self.cpu.X == 0) # Only Z affected

    def _execute_jmp(self, mode): self.cpu.PC = self._get_effective_address(mode)

    def _execute_jsr(self, mode):
        # JSR: PC of next instruction is pushed. PC is already advanced by fetching opcode.
        # Then, fetch operand for JSR (advancing PC further).
        # The PC value *after* fetching JSR's own operand is what's pushed.
        if mode == MODE_INDEXED:
            offset = self._fetch_operand_byte() # PC advances by 1
            return_addr = self.cpu.PC
            target_addr = (self.cpu.X + offset) & 0xFFFF
        elif mode == MODE_EXTENDED:
            target_addr_word = self._fetch_operand_word() # PC advances by 2
            return_addr = self.cpu.PC
            target_addr = target_addr_word
        else: # Should not happen if opcode table is correct
            self.cpu.is_halted = True; return
        self.cpu.push_word_to_stack(return_addr)
        self.cpu.PC = target_addr

    def _execute_ldaa(self, mode):
        val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        self.cpu.A = val
        self.cpu.set_nz_flags(self.cpu.A); self.cpu.CCR.V = False

    def _execute_ldab(self, mode):
        val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        self.cpu.B = val
        self.cpu.set_nz_flags(self.cpu.B); self.cpu.CCR.V = False

    def _execute_lds(self, mode):
        val = self._fetch_operand_word() if mode == MODE_IMMEDIATE else self.cpu.memory.read_word(self._get_effective_address(mode))
        self.cpu.SP = val
        self.cpu.set_nz_flags_16bit(self.cpu.SP); self.cpu.CCR.V = False

    def _execute_ldx(self, mode):
        val = self._fetch_operand_word() if mode == MODE_IMMEDIATE else self.cpu.memory.read_word(self._get_effective_address(mode))
        self.cpu.X = val
        self.cpu.set_nz_flags_16bit(self.cpu.X); self.cpu.CCR.V = False

    def _execute_lsr(self, mode): # Logical Shift Right (Memory)
        eff_addr = self._get_effective_address(mode)
        val = self.cpu.memory.read_byte(eff_addr)
        self.cpu.CCR.C = bool(val & 0x01)
        val >>= 1
        self.cpu.memory.write_byte(eff_addr, val)
        self.cpu.CCR.N = False # N is always cleared
        self.cpu.CCR.Z = (val == 0)
        self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C # V = N xor C (here N=0, so V=C)

    def _execute_lsra(self, mode):
        self.cpu.CCR.C = bool(self.cpu.A & 0x01)
        self.cpu.A >>= 1
        self.cpu.CCR.N = False; self.cpu.CCR.Z = (self.cpu.A == 0)
        self.cpu.CCR.V = self.cpu.CCR.C # N=0, so V=C

    def _execute_lsrb(self, mode):
        self.cpu.CCR.C = bool(self.cpu.B & 0x01)
        self.cpu.B >>= 1
        self.cpu.CCR.N = False; self.cpu.CCR.Z = (self.cpu.B == 0)
        self.cpu.CCR.V = self.cpu.CCR.C # N=0, so V=C

    def _execute_neg(self, mode): # Negate Memory (2's Complement)
        eff_addr = self._get_effective_address(mode)
        val = self.cpu.memory.read_byte(eff_addr)
        res = (-val) & 0xFF
        self.cpu.memory.write_byte(eff_addr, res)
        self.cpu.set_nz_flags(res)
        self.cpu.CCR.V = (res == 0x80) # V set if result is $80
        self.cpu.CCR.C = (res != 0x00) # C set if result is not $00 (borrow from bit 7)

    def _execute_nega(self, mode):
        res = (-self.cpu.A) & 0xFF
        self.cpu.A = res
        self.cpu.set_nz_flags(res); self.cpu.CCR.V = (res == 0x80); self.cpu.CCR.C = (res != 0x00)

    def _execute_negb(self, mode):
        res = (-self.cpu.B) & 0xFF
        self.cpu.B = res
        self.cpu.set_nz_flags(res); self.cpu.CCR.V = (res == 0x80); self.cpu.CCR.C = (res != 0x00)

    def _execute_nop(self, mode): pass

    def _execute_oraa(self, mode): # Inclusive OR A
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        self.cpu.A |= mem_val
        self.cpu.set_nz_flags(self.cpu.A); self.cpu.CCR.V = False

    def _execute_orab(self, mode): # Inclusive OR B
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        self.cpu.B |= mem_val
        self.cpu.set_nz_flags(self.cpu.B); self.cpu.CCR.V = False

    def _execute_psha(self, mode): self.cpu.push_byte_to_stack(self.cpu.A)
    def _execute_pshb(self, mode): self.cpu.push_byte_to_stack(self.cpu.B)

    def _execute_pula(self, mode): self.cpu.A = self.cpu.pop_byte_from_stack() # PULL does not affect flags in M6800
    def _execute_pulb(self, mode): self.cpu.B = self.cpu.pop_byte_from_stack()

    def _execute_rol(self, mode): # Rotate Left (Memory)
        eff_addr = self._get_effective_address(mode)
        val = self.cpu.memory.read_byte(eff_addr)
        c_in = self.cpu.CCR.C
        self.cpu.CCR.C = bool(val & 0x80) # Bit 7 to Carry
        val = ((val << 1) | (1 if c_in else 0)) & 0xFF
        self.cpu.memory.write_byte(eff_addr, val)
        self.cpu.set_nz_flags(val)
        self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C

    def _execute_rola(self, mode):
        c_in = self.cpu.CCR.C; self.cpu.CCR.C = bool(self.cpu.A & 0x80)
        self.cpu.A = ((self.cpu.A << 1) | (1 if c_in else 0)) & 0xFF
        self.cpu.set_nz_flags(self.cpu.A); self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C

    def _execute_rolb(self, mode):
        c_in = self.cpu.CCR.C; self.cpu.CCR.C = bool(self.cpu.B & 0x80)
        self.cpu.B = ((self.cpu.B << 1) | (1 if c_in else 0)) & 0xFF
        self.cpu.set_nz_flags(self.cpu.B); self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C

    def _execute_ror(self, mode): # Rotate Right (Memory)
        eff_addr = self._get_effective_address(mode)
        val = self.cpu.memory.read_byte(eff_addr)
        c_in = self.cpu.CCR.C
        self.cpu.CCR.C = bool(val & 0x01) # Bit 0 to Carry
        val = ((val >> 1) | (0x80 if c_in else 0)) & 0xFF
        self.cpu.memory.write_byte(eff_addr, val)
        self.cpu.set_nz_flags(val)
        self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C

    def _execute_rora(self, mode):
        c_in = self.cpu.CCR.C; self.cpu.CCR.C = bool(self.cpu.A & 0x01)
        self.cpu.A = ((self.cpu.A >> 1) | (0x80 if c_in else 0)) & 0xFF
        self.cpu.set_nz_flags(self.cpu.A); self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C

    def _execute_rorb(self, mode):
        c_in = self.cpu.CCR.C; self.cpu.CCR.C = bool(self.cpu.B & 0x01)
        self.cpu.B = ((self.cpu.B >> 1) | (0x80 if c_in else 0)) & 0xFF
        self.cpu.set_nz_flags(self.cpu.B); self.cpu.CCR.V = self.cpu.CCR.N ^ self.cpu.CCR.C

    def _execute_rti(self, mode): # Return from Interrupt
        # Stack order (from top, so pop in this order): CCR, B, A, XH, XL, PCH, PCL
        # So pop PCL, PCH, XL, XH, A, B, CCR
        # No, SWI pushes PC, IX, A, B, CC. So RTI pops CC, B, A, IX, PC
        self.cpu.CCR.set_from_byte(self.cpu.pop_byte_from_stack())
        self.cpu.B = self.cpu.pop_byte_from_stack()
        self.cpu.A = self.cpu.pop_byte_from_stack()
        self.cpu.X = self.cpu.pop_word_from_stack() # pop_word_from_stack MSB then LSB (as pushed by push_word)
        self.cpu.PC = self.cpu.pop_word_from_stack()

    def _execute_rts(self, mode): self.cpu.PC = self.cpu.pop_word_from_stack()

    def _execute_sba(self, mode): # Subtract B from A (A - B -> A)
        a_old = self.cpu.A
        b_val = self.cpu.B
        res16 = a_old - b_val
        self.cpu.A = res16 & 0xFF
        self._set_flags_add_sub(a_old, b_val, self.cpu.A, is_sub=True)

    def _execute_sbca(self, mode): # Subtract with Carry from A (A - M - C -> A)
        a_old = self.cpu.A
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        carry_in = self.cpu.CCR.C # Borrow in
        res16 = a_old - mem_val - (1 if carry_in else 0)
        self.cpu.A = res16 & 0xFF
        self._set_flags_add_sub(a_old, mem_val, self.cpu.A, is_sub=True, with_carry=True, carry_in=carry_in)

    def _execute_sbcb(self, mode): # Subtract with Carry from B (B - M - C -> B)
        b_old = self.cpu.B
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        carry_in = self.cpu.CCR.C
        res16 = b_old - mem_val - (1 if carry_in else 0)
        self.cpu.B = res16 & 0xFF
        self._set_flags_add_sub(b_old, mem_val, self.cpu.B, is_sub=True, with_carry=True, carry_in=carry_in)

    def _execute_sec(self, mode): self.cpu.CCR.C = True
    def _execute_sei(self, mode): self.cpu.CCR.I = True
    def _execute_sev(self, mode): self.cpu.CCR.V = True

    def _execute_staa(self, mode):
        eff_addr = self._get_effective_address(mode)
        self.cpu.memory.write_byte(eff_addr, self.cpu.A)
        self.cpu.set_nz_flags(self.cpu.A); self.cpu.CCR.V = False

    def _execute_stab(self, mode):
        eff_addr = self._get_effective_address(mode)
        self.cpu.memory.write_byte(eff_addr, self.cpu.B)
        self.cpu.set_nz_flags(self.cpu.B); self.cpu.CCR.V = False

    def _execute_sts(self, mode): # Store Stack Pointer
        eff_addr = self._get_effective_address(mode)
        self.cpu.memory.write_word(eff_addr, self.cpu.SP)
        self.cpu.set_nz_flags_16bit(self.cpu.SP); self.cpu.CCR.V = False

    def _execute_stx(self, mode): # Store Index Register
        eff_addr = self._get_effective_address(mode)
        self.cpu.memory.write_word(eff_addr, self.cpu.X)
        self.cpu.set_nz_flags_16bit(self.cpu.X); self.cpu.CCR.V = False

    def _execute_suba(self, mode): # Subtract from A (A - M -> A)
        a_old = self.cpu.A
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        res16 = a_old - mem_val
        self.cpu.A = res16 & 0xFF
        self._set_flags_add_sub(a_old, mem_val, self.cpu.A, is_sub=True)

    def _execute_subb(self, mode): # Subtract from B (B - M -> B)
        b_old = self.cpu.B
        mem_val = self._fetch_operand_byte() if mode == MODE_IMMEDIATE else self.cpu.memory.read_byte(self._get_effective_address(mode))
        res16 = b_old - mem_val
        self.cpu.B = res16 & 0xFF
        self._set_flags_add_sub(b_old, mem_val, self.cpu.B, is_sub=True)

    def _execute_swi(self, mode): # Software Interrupt
        # M6800 SWI Stack Order: PC(L), PC(H), X(L), X(H), A, B, CCR
        # Push order: CCR, B, A, X, PC (to get correct stack order)
        self.cpu.push_word_to_stack(self.cpu.PC) # PC (dönüş adresi, SWI sonrası)
        self.cpu.push_word_to_stack(self.cpu.X)
        self.cpu.push_byte_to_stack(self.cpu.A)
        self.cpu.push_byte_to_stack(self.cpu.B)
        self.cpu.push_byte_to_stack(self.cpu.CCR.get_byte())
        self.cpu.CCR.I = True # Set Interrupt Mask
        self.cpu.PC = self.cpu.memory.read_word(0xFFFA) # Load PC from SWI vector
        # self.cpu.is_halted = True # Genellikle SWI sonrası program devam eder, OS handler'a atlar. Simülatörde durdurabiliriz.

    def _execute_tab(self, mode): # Transfer A to B
        self.cpu.B = self.cpu.A
        self.cpu.set_nz_flags(self.cpu.B); self.cpu.CCR.V = False

    def _execute_tap(self, mode): # Transfer A to CCR
        # CCR bits 7,6 are always 1. A's low 6 bits go to HINZVC.
        val_a = self.cpu.A & 0x3F # Mask low 6 bits of A
        self.cpu.CCR.set_from_byte(0xC0 | val_a) # Combine with 11000000

    def _execute_tba(self, mode): # Transfer B to A
        self.cpu.A = self.cpu.B
        self.cpu.set_nz_flags(self.cpu.A); self.cpu.CCR.V = False

    def _execute_tpa(self, mode): # Transfer CCR to A
        self.cpu.A = self.cpu.CCR.get_byte()
        # N, Z, V flags are not affected by TPA itself.

    def _execute_tst(self, mode): # Test Memory (M - 00)
        eff_addr = self._get_effective_address(mode)
        val = self.cpu.memory.read_byte(eff_addr)
        self.cpu.set_nz_flags(val)
        self.cpu.CCR.V = False; self.cpu.CCR.C = False # V and C are cleared

    def _execute_tsta(self, mode): self.cpu.set_nz_flags(self.cpu.A); self.cpu.CCR.V = False; self.cpu.CCR.C = False
    def _execute_tstb(self, mode): self.cpu.set_nz_flags(self.cpu.B); self.cpu.CCR.V = False; self.cpu.CCR.C = False

    def _execute_tsx(self, mode): # Transfer Stack Pointer to Index Reg (SP+1 -> X)
        self.cpu.X = (self.cpu.SP + 1) & 0xFFFF
        # No flags affected

    def _execute_txs(self, mode): # Transfer Index Reg to Stack Pointer (X-1 -> SP)
        self.cpu.SP = (self.cpu.X - 1) & 0xFFFF
        # No flags affected

    def _execute_wai(self, mode): # Wait for Interrupt
        # If I=0, CPU waits for interrupt. All registers pushed to stack like SWI.
        # If I=1, WAI behaves like NOP.
        if not self.cpu.CCR.I:
            # Push state like SWI (order may vary slightly in some docs for WAI vs SWI)
            self.cpu.push_word_to_stack(self.cpu.PC)
            self.cpu.push_word_to_stack(self.cpu.X)
            self.cpu.push_byte_to_stack(self.cpu.A)
            self.cpu.push_byte_to_stack(self.cpu.B)
            self.cpu.push_byte_to_stack(self.cpu.CCR.get_byte())
            self.cpu.is_halted = True # Simulate waiting
            # Actual interrupt handling would involve interrupt vectors.
            print("WAI: CPU halted, waiting for interrupt (I=0).")
        else:
            # print("WAI: Behaves like NOP (I=1).")
            pass # NOP