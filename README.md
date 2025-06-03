

# **Sistem Tasarımı**

**Geliştirilen SDK, modüler bir mimari üzerine kurulmuş olup temel olarak üç ana bileşenden oluşmaktadır: Assembler, Simülatör ve Kullanıcı Arayüzü. Bu bileşenler, görev ayrımı prensibine uygun olarak tasarlanmış ve Python programlama dili kullanılarak implemente edilmiştir.**

##  **Assembler Mimarisi**

**Assembler, M6800 assembly kaynak kodunu makine koduna (nesne kodu) çevirmekle görevlidir. Bu süreç  iki geçişli (two-pass) yaklaşımıyla gerçekleştirilmiştir. Bu yöntem forward referencesin etkin bir şekilde çözümlenmesine olanak tanır.**

**Birinci Geçiş (Pass 1): Bu aşamada kaynak kod satır satır taranır. LexicalAnalyzer modülü tarafından her satır sözcüksel birimlere (token'lara: etiket, mnemonik, operand, yorum) ayrıştırılır. Ardından, SyntaxAnalyzer modülü bu token'ları alarak temel sözdizimi kontrollerini yapar ve ParsedInstruction nesneleri oluşturur.** 

**En kritik görevlerden biri olan sembol tablosunun (SymbolTable) oluşturulması bu geçişte yapılır. Karşılaşılan her etiket, o anki Konum Sayacı (Location Counter - LC) değeri ile birlikte sembol tablosuna kaydedilir. LC, her komutun veya veri tanımlama direktifinin (örn: FCB, RMB) bellekte kaplayacağı byte sayısına göre güncellenir. ORG direktifi ile LC doğrudan ayarlanabilir. Bu geçişin sonunda, programdaki tüm etiketlerin adresleri belirlenmiş olur.**

**İkinci Geçiş (Pass 2): Bu aşamada birinci geçişte oluşturulan ParsedInstruction listesi ve doldurulmuş sembol tablosu kullanılır. CodeGenerator modülü, her bir ParsedInstruction için makine kodunu üretir. Komut operandlarında yer alan etiketler, sembol tablosundan karşılık gelen adreslerle değiştirilir. Dallanma (branch) komutları için hedef etiket ile mevcut komut adresi arasındaki offset hesaplanır. Üretilen makine kodu byte dizisi ve her kaynak satırına karşılık gelen detayları içeren bir listing dosyası oluşturulur.**

**  
  

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXfvGov0YKYIyeORx7rirn7osmusOw2rfv_Kt_9YoPxQmenrhj-DfELUSU2xCFpoYXRodf86jHHt8-Me60naxprVh81VgWwk4EaEgSOpUJmfSWQUO3krtKJab-EpsgDcXmTjUeqi4g?key=cZKUb2HtPJWYIRwa8MP5gA)

  

## Simülatör Mimarisi

Simülatör, assembler tarafından üretilen makine kodunu sanal bir M6800 CPU üzerinde yürüterek programın davranışının gözlemlenmesini sağlar.

cpu.py: M6800 CPU'nun temel elemanlarını (Akümülatör A, Akümülatör B, Index Register X, Program Counter PC, Stack Pointer SP) ve Durum Kod Register'ını (CCR - H, I, N, Z, V, C flag'leri) simüle eder. Ayrıca, 64KB'lık bir bellek (Memory sınıfı) de bu modül içinde yönetilir. Bellek okuma, yazma ve program yükleme işlemleri bu sınıf üzerinden gerçekleştirilir.

instruction\_executor.py: Her bir M6800 makine kodu komutunun CPU üzerindeki etkisini (register değerlerini değiştirme, bellek erişimi, CCR flag'lerini güncelleme) tanımlayan mantığı içerir. Okunan opkoda karşılık gelen yürütme fonksiyonunu bir dispatch tablosu aracılığıyla çağırır.

simulator.py: Simülasyon sürecini yönetir. Nesne kodunu CPU belleğine yükler, CPU'yu başlangıç durumuna getirir (reset), komutların adım adım (step) veya sürekli (run) çalıştırılmasını sağlar. Breakpoint yönetimi ve UI ile iletişim için callback mekanizmalarını içerir.

  

## Modüler Yapı ve Dosya Organizasyonu

Proje, sorumlulukların net bir şekilde ayrıldığı modüler bir dosya yapısına sahiptir:

assembler/: Assembler ile ilgili tüm mantığı (lexical analiz, syntax analiz, kod üretimi, sembol tablosu, opkod tablosu) içerir.

simulator/: CPU modeli, komut yürütme ve simülatör kontrolü gibi simülasyonla ilgili mantığı barındırır.

ui/: Tkinter kullanılarak geliştirilen kullanıcı arayüzü bileşenlerini içerir.

main.py: Uygulamanın ana giriş noktasıdır ve kullanıcı arayüzünü başlatır.


# Komut Seti Yönetimi (Instruction Set Handling)

M6800 komut setinin ve a pseudo-operation yönetimi, sistemin doğruluğu ve genişletilebilirliği açısından önem arz etmektedir.

## Opcode Tablosu (opcode\_table.py)

Tüm M6800 mnemonikleri, bu mnemoniklerin farklı adresleme modlarındaki opkodları, komutların byte uzunlukları, CPU döngü süreleri ve etkiledikleri CCR flag'leri merkezi bir Python sözlüğü (INSTRUCTION\_SET) içinde tanımlanmıştır.

Her mnemonik için  desteklenen her adresleme modu (örn: MODE\_IMMEDIATE, MODE\_DIRECT, MODE\_EXTENDED, MODE\_INDEXED, MODE\_IMPLIED, MODE\_RELATIVE) ayrı bir alt sözlükte detaylandırılmıştır. Bu detaylar, 'opcode', 'bytes', 'cycles', 'flags\_affected' gibi anahtarlarla saklanır.

Benzer şekilde, assembler direktifleri (ORG, EQU, FCB, FDB, RMB, END) de 'PSEUDO\_OPS' adlı bir sözlükte, bekledikleri parametre sayısı ve türü gibi bilgilerle tanımlanmıştır.

## Komutların İşlenmesi

Assembler Tarafında

LexicalAnalyzer, kaynak koddaki mnemonik string'ini ayıklar. SyntaxAnalyzer, bu mnemonik string'ini kullanarak opcode\_table.py'den ilgili komutun tanımını alır. Kaynak koddaki operandlara bakarak, opcode\_table'da tanımlı olan ve operandlarla eşleşen geçerli adresleme modunu belirler. Bu moda özgü opcode ve byte sayısı gibi bilgiler ParsedInstruction nesnesine kaydedilir.

CodeGenerator, ParsedInstruction'daki opcode ve çözümlenmiş operandları kullanarak makine kodunu üretir.

  

Simülatör Tarafında

InstructionExecutor, bellekten okuduğu opcodeyi alır. Bu opcode’a karşılık gelen mnemonik, adresleme modu ve diğer statik bilgileri (döngü sayısı, etkilenecek flag'ler) yine opcode\_table.py'deki INSTRUCTION\_SET üzerinden bulur (veya dispatch\_table aracılığıyla önceden eşleştirilmiş handler fonksiyonunu çağırır).

Her komut için özel olarak yazılmış \_execute\_MNEMONIC metodunda, komutun CPU üzerindeki etkisi (register değişiklikleri, bellek işlemleri) ve flag güncellemeleri, opcode\_table'dan alınan bu statik bilgilere ve komutun kendi mantığına göre gerçekleştirilir.

# Kullanıcı Arayüzü

Kullanıcı arayüzü, Python'un GUI kütüphanesi olan Tkinter kullanılarak geliştirilmiştir.

## Ana Pencere Düzeni

Uygulama, ana işlevleri mantıksal olarak gruplayan iki ana panele ayrılmıştır: sol panel kodlama ve çıktı görüntüleme için, sağ panel ise simülasyon kontrolü ve durum takibi içindir.

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXfGn0EQwrWp-Cb1x_MNtWWlxNcsZ_9Bpz7pjeRLGy3P0EQFpQd1xcKrr54WNS4M_Iv5oJMpjjt5MzP0hi0yO402LLk2kPXJD5nw5pJpC6jFEgG33oqeeT0C9P92ctR1noYaB5idSA?key=cZKUb2HtPJWYIRwa8MP5gA)

  

## Kod Editörü ve Çıktı Alanları (Sol Panel)

Assembly Kod Editörü: Kullanıcıların M6800 assembly kodlarını yazabildikleri veya mevcut dosyaları açıp düzenleyebildikleri, kaydırma çubuklu bir metin alanıdır. Temel metin düzenleme işlevlerini (geri alma vb.) destekler.

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXcKL2PkRnC_SrXXgKqFfrDH9OS-kBa98QlotkFcAFbS9qwBcJhegaWm6_RAnUMvp25mpm2iUap8ow_IoQI938FLkpHHyqrdoXc66qzy6DYkFjobeLj0We4qKg8aTbBXDZL2GMgYYg?key=cZKUb2HtPJWYIRwa8MP5gA)

  

## Çıktı Sekmeleri

Object Code (Hex) Sekmesi: "Assemble" işlemi başarıyla tamamlandığında, üretilen makine kodunun hexadecimal (onaltılık) temsili bu alanda gösterilir. Bu, kullanıcıların çevrilen kodu doğrudan görmelerini sağlar.

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXcfBKh2xbvVn6_VZX2FTYx4eWtG7kcIbSkhKc8A8LnGS3YEQjmfA5_Xe3EeFsGmsHeyPar9cX_5f4nklMTdcw9M-1lcIwyOzfbRMeyVo6HzRmfHvCu7PoHnlE4RIOwb6pOZVzfG?key=cZKUb2HtPJWYIRwa8MP5gA)

  

Listing / Mapping Sekmesi: "Assemble" işlemi sonrasında, her bir kaynak kod satırına karşılık gelen bellek adresi, üretilen hexadecimal makine kodu (varsa), orijinal kaynak kod satırı ve olası derleme hataları veya yorumlar bir tablo (ttk.Treeview) formatında sunulur. Hatalı satırlar, kullanıcıların sorunları kolayca tespit edebilmesi için görsel olarak (vurgulanır. Bu tablo, kullanıcıların assembly kodları ile üretilen makine kodları arasındaki eşleşmeyi satır satır takip etmelerine olanak tanır. Kullanıcılar, bu tablodaki bir satıra sağ tıklayarak hata mesajını panoya kopyalayabilirler.

Başarılı Kod Örneği

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXd-XZnLj_CMa1oPl-xjL5L3CA4CKMrePJAjMwc9BGxBO35mEtqF8bTWDaP52lTv-qgBpjFvuEM48sp-mDW_MD_K_G9TqJkFHVSFaUvszyTsO60-yduHM9FZsQiqCT_Qu3JkugiQtQ?key=cZKUb2HtPJWYIRwa8MP5gA)

Hatalı Syntax

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXcf1OHiiJ3Ab3ExFcnD5s0ZsAsgkaBtS1JibNASWnHsnuBI2SCkSScGIuhVCyxf6gcGhvuyVe9uHBWs5NO5k0xrSo3puCNPJRMxfm431KtdEVHXdsla83km82xtuiJSjqVxeFiebw?key=cZKUb2HtPJWYIRwa8MP5gA)

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXfPISC1hby7ETCx_v2zK6vTNrzan8JtDSzGVeh0wWIJKjwbecVSzV1QFaDdIB6DqCnYkJqxIrSMJT5YP_P70lHl9SOOyZXxOePZNIBxCCKIeUupd71qneHN3QeNvGjd51uhZ3w?key=cZKUb2HtPJWYIRwa8MP5gA)

## Simülasyon Kontrolleri ve Durum Göstergeleri

Controls Butonları:

Assemble: Kod editöründeki mevcut assembly kodunu derler.

Load to Sim: Başarıyla derlenmiş nesne kodunu simülatör belleğine yükler.

Run: Simülatörü sürekli modda çalıştırır (bir breakpoint'e veya durma komutuna kadar).

Step: Tek bir M6800 komutunu yürütür.

Stop: Sürekli çalışan simülasyonu durdurur.

Reset CPU: Simülatör CPU'sunu başlangıç durumuna sıfırlar.

  

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXftgfgLhJnmHOeCUGKYBo2cMdr0Y0yZuM2ibjIC3D6RD11eB_0_vuAE4NBz_y86X1i_VsCfGXh5vJuoAxXarlziZLMRjdI5m4pSt5p0kJgxPDBTbNJPMtXumn903NFosYbUW6ieQg?key=cZKUb2HtPJWYIRwa8MP5gA)

CPU Registers Paneli: M6800 CPU'nun Akümülatör A, Akümülatör B, Index Register X, Program Counter (PC), Stack Pointer (SP) ve Durum Kod Register'ının (CCR - H, I, N, Z, V, C flag'leri ve hex değeri) güncel değerleri bu alanda simülasyon sırasında canlı olarak gösterilir ve her adımda güncellenir.

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXe0aNHSp6oB3VZF4YR_d85MbcP-qPvR_OsM0IgGvRj0a2ixS3gCIdlj12YPHtqmDnl9S4xby4uKxncNEswDNYYm3kBkBlVqNBnVohcQZ9TIjFzv0UpmF4qBxOZVgbJmWEhT25B_Kg?key=cZKUb2HtPJWYIRwa8MP5gA)

Memory View Paneli: Kullanıcının simülatör belleğinin belirli bir bölümünü incelemesine olanak tanır. "Go to Addr (Hex)" alanına istenen bellek adresi (hex olarak) girilip "Go" butonuna tıklandığında, o adresten itibaren bellek içeriği hem hexadecimal hem de okunabilir ASCII karakterler olarak listelenir. Bu, programın bellekte yaptığı değişikliklerin takibi için kritik öneme sahiptir.

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXfH9qj4geLptl3CDNyEyYLqWvtMVMDr0aLDoiNKkC7sOzrt_WWESAXjg2NoTUt0kmtKBHBm_i1mWam6iy0Iwd0RQ0XalK5HqpFmkiCHcMjAgmEJRb9agOctSsYP8pI8-6a5r3js3g?key=cZKUb2HtPJWYIRwa8MP5gA)

  

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXdJm_BelGCIN37mwfifYM4aM_pNjyfFJ1jEwgXlCgB7ZY83rsTK5JYVTu-36M63QlkEp8_4kVwRWlxkN9jzDzjAKnrdG4yMCBdq4jQB9No6ErC-ys6iM5jFPWHHalWLNwaBRKGV?key=cZKUb2HtPJWYIRwa8MP5gA)

## Menü Çubuğu ve Durum Çubuğu

Menü Çubuğu: Dosya işlemleri (File), derleme (Build), simülasyon kontrolleri (Debug) ve yardım (Help) gibi temel işlevlere erişim sağlar.

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXcF63Xk731j80LN4lvzG1hluZaWYXYdKxVCZmnacutTrZJGxOldibNmiJB22o2sDZ-BPx0xNu4FnigIWN1_b5yNSrBbn9RBpBFUdH6WTUEUoT4AUMNeUiiCChSLs0Jci0bKpue9_Q?key=cZKUb2HtPJWYIRwa8MP5gA)![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXdftawltKGrHwsqjrlepQlIojvB8H7yopOYKepx2H55bHbbicwvXmKVfrIQupoEUPv0By_nk3Z7dETu0lJ6Q8vgpwwIJw0bmyklzFqqRyyoAcptJWTsyMB2nw0PE9wn5QmTpVF5QQ?key=cZKUb2HtPJWYIRwa8MP5gA)![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXe22CBQaD_d6SqEpglDMpvVaYpCt6HBOE1gmltJ8Xh2UaGG_70yblpB7WTSzUu1gIB5tuveElyi0-zwCu6ZRiT-i6Znnf08sWH10iR816uc_kHcLJx_WOhzTIwROxNf51aDGodSnA?key=cZKUb2HtPJWYIRwa8MP5gA)

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXewKgFQvfCO_YPiUZaDGsy9-0nK93xW9MPjrYxC2yr_C1J082rCFDZ4590Bjn1v74SV1Rtapw5pg_vyY4eSi0X5mDOLiaaHX6PtJ6dMDQs1sf09rGKmnwWaEo7re8NTEkLi5bs5GA?key=cZKUb2HtPJWYIRwa8MP5gA)

Durum Çubuğu (Status Bar): Uygulamanın en altında yer alır ve kullanıcıya güncel işlem durumu (örn: "Assembling...", "Simulation Halted.", "Ready.") veya kısa hata mesajları hakkında bilgi verir.

![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXcOQBQAJ4TZu00OpaMvif6_v5KQGIMngTl3C1GbOID24xXVARsWw6VGciCNxH7UeQCsfpbTN0e2jQQUVCuOk-XdXBxtEQS4LuRVfHFAk6vqjCOK96H7xbl96YFwqfPOAkC8HrbTvA?key=cZKUb2HtPJWYIRwa8MP5gA)

  
**ch text content here. You can paste directly from Word or other rich text sources.
