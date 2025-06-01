import re

class Token:
    """
    Bir assembly satırının ayrıştırılmış bileşenlerini temsil eder.
    """
    def __init__(self, line_number, original_line, label=None, mnemonic=None, operands=None, comment=None):
        self.line_number = line_number
        self.original_line = original_line.strip()
        self.label = label.upper() if label else None
        self.mnemonic = mnemonic.upper() if mnemonic else None # Mnemonik ve direktifler büyük harf
        self.operands_raw_str = operands # Operandları ham string olarak tutalım, syntax analizi sonra yapsın
        self.comment = comment

    def __repr__(self):
        return (f"Token(L:{self.line_number}, Label='{self.label}', Mnemonic='{self.mnemonic}', "
                f"Operands='{self.operands_raw_str}', Comment='{self.comment}')")

class LexicalAnalyzer:
    def __init__(self):
        # Regex ile bir assembly satırını parçalamak için desenler
        # Bu desen M6800 için daha spesifik hale getirilebilir.
        # Örnek: (Label)? (Mnemonic) (Operands)? (Comment)?
        # Label: isteğe bağlı, alfa-numerik, ':' ile bitebilir (veya boşlukla ayrılır)
        # Mnemonic: alfa-numerik
        # Operands: virgüülle ayrılmış olabilir, özel karakterler içerebilir (#, $, ,X)
        # Comment: ';' veya '*' ile başlar

        # Basit bir regex, daha karmaşık durumlar için geliştirilebilir.
        # Bu regex, satır başındaki boşlukları ve etiket sonrası boşlukları dikkate alır.
        # Grup 1: Label (isteğe bağlı, sonda ':' olabilir veya olmayabilir)
        # Grup 2: Mnemonic/Directive
        # Grup 3: Operands (isteğe bağlı)
        # Grup 4: Comment (isteğe bağlı, ';' veya '*' ile başlayan)
        self.line_regex = re.compile(
            r"^\s*(?:([a-zA-Z_][a-zA-Z0-9_]*)(?::|\s+))?"  # 1: Label (isteğe bağlı)
            r"\s*([a-zA-Z]{2,5})"                         # 2: Mnemonic/Directive (2-5 harf)
            r"(?:\s+([^;*]*?))?"                          # 3: Operands (isteğe bağlı, yorum öncesine kadar)
            r"\s*(?:([;*].*))?$"                          # 4: Comment (isteğe bağlı)
            , re.IGNORECASE) # Büyük/küçük harf duyarsız

        # Sadece yorum veya boş satırları yakalamak için
        self.comment_or_empty_regex = re.compile(r"^\s*([;*].*)?$|^\s*$")


    def tokenize_line(self, line_number, line_text):
        """
        Tek bir assembly satırını token'larına ayırır.
        """
        line_text = line_text.strip()

        # Sadece yorum veya boş satır mı kontrol et
        match_comment_empty = self.comment_or_empty_regex.match(line_text)
        if match_comment_empty:
            comment_content = match_comment_empty.group(1) if match_comment_empty.group(1) else None
            if line_text == "" and not comment_content : # Tamamen boş satırsa
                return None # Boş satırlar için None döndür, işlenmesin
            return Token(line_number, line_text, comment=comment_content)


        match = self.line_regex.match(line_text)
        if match:
            label, mnemonic, operands, comment = match.groups()

            # Etiketteki ':' karakterini temizle (eğer varsa)
            if label and label.endswith(':'):
                label = label[:-1]

            # Operandlar varsa, baştaki/sondaki boşlukları temizle
            operands_str = operands.strip() if operands else None

            return Token(line_number, line_text, label, mnemonic, operands_str, comment)
        else:
            # Eğer satır yukarıdaki regex'e uymuyorsa, bu bir syntax hatası olabilir
            # veya satır sadece bir etiket ve yorumdan oluşuyor olabilir.
            # Şimdilik bunu bir hata olarak işaretleyebiliriz veya daha esnek bir ayrıştırma deneyebiliriz.
            # Örnek: Sadece etiket varsa ve komut yoksa
            label_only_match = re.match(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)(?::|\s+)?\s*([;*].*)?$", line_text, re.IGNORECASE)
            if label_only_match:
                label = label_only_match.group(1)
                comment = label_only_match.group(2)
                if label and label.endswith(':'):
                    label = label[:-1]
                return Token(line_number, line_text, label=label, comment=comment)

            # Bilinmeyen format veya hata
            print(f"Warning: Line {line_number} could not be fully parsed: '{line_text}'") # Geçici uyarı
            # Daha iyi hata yönetimi için burada bir hata token'ı döndürülebilir.
            return Token(line_number, line_text, comment=f"LEXICAL_ERROR: Invalid format: {line_text}")


    def tokenize_source_code(self, source_code_str):
        """
        Tüm kaynak kodunu (string olarak) alır ve token listesi döndürür.
        """
        tokens = []
        lines = source_code_str.splitlines()
        for i, line in enumerate(lines):
            token = self.tokenize_line(i + 1, line)
            if token: # None olmayan (boş olmayan) token'ları ekle
                tokens.append(token)
        return tokens

# Test için örnek kullanım
if __name__ == "__main__":
    lexer = LexicalAnalyzer()

    sample_code = """
    STARTADR EQU $1000    ; Program başlangıç adresi
    LOOP: LDAA #$05      ; A'ya 5 yükle
          DECA
          BNE  LOOP      ; LOOP'a dallan eğer sıfır değilse
          ANDA #%00001111 ; Maskeleme
    * Sadece yorum satırı
          LDAB DATA,X
    VALUE FCB $10, $20, $30
          ORG  STARTADR
          NOP              ; No operation
          END
    LABELONLY:
    ; son yorum
    """

    print("--- Tokenizing Sample Code ---")
    token_list = lexer.tokenize_source_code(sample_code)
    for t in token_list:
        print(t)

    print("\n--- Testing individual lines ---")
    test_lines = [
        "MYLABEL: LDAA #$FF",
        "         ADDB VALUE",
        "NOOP", # Bu mnemonik "NOP" olmalı, regex bunu yakalayabilir ama syntax'ta hata verir
        "LOOP:    DECA       ; Decrement A",
        "         BNE  LOOP",
        "* This is a full line comment",
        "         FCB  $01,$02,$03 ; Define bytes",
        "         ORG  $C000",
        "LABEL_NO_CMD: ; Sadece etiket ve yorum",
        "           END",
        "INVALID LINE HERE", # Hata durumu
        "LONE_LABEL:",
        "" # Boş satır
    ]

    for i, tl in enumerate(test_lines):
        print(f"Line {i+1}: '{tl}' -> {lexer.tokenize_line(i+1, tl)}") 
