

# Kullanıcı Arayüzü

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

  
