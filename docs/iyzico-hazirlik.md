# iyzico başvurusu için yapılan hazırlık

20 Ekim 2026 tarihinde resmi gereklilikler incelendi:
https://www.iyzico.com/isim-icin/sanal-pos
https://docs.iyzico.com/ek-bilgiler/iyzico-logo-paketi
https://docs.iyzico.com/odeme-metotlari/odeme-formu

Hakkımızda, iletişim, gizlilik, mesafeli satış, teslimat ve iade sayfaları erişilebilir. Görseldeki VKN, vergi dairesi ve kayıtlı adres kullanıldı. Gerçekliği doğrulanamayan limited şirket, sicil, MERSİS, KEP ve teknopark iddiaları kaldırıldı. Banka hesabı yeni IBAN ile güncellendi; yalnızca bir hesap gösterilir. IBAN uzunluğu ve MOD97 kontrolü geçerlidir; bu kontrol hesap sahipliğini doğrulamaz.

## Tamamlanmayı bekleyenler

- Kullanıcı kişisel adların yayımlanmamasını açıkça istedi. Şahıs işletmesinin resmi satıcı adı bu nedenle yayımlanmıyor. iyzico'nun satıcı kimliği şartı tam karşılanmış değildir; isim gizleme tercihi ile başvuru gerekliliği birlikte çözülmelidir.
- KEP ve varsa MERSİS/sicil/meslek odası bilgileri sağlanmadı. Uydurma kayıtlar eklenmedi.
- iyzico başvuru onayı, işletme belgeleri ve gerçek sunucu entegrasyonu tamamlanmadı. İşyeri hesabına erişilmedi, ödeme alınmadı.
- Sunucuda gizli API anahtarları ile CheckoutForm başlatma, tutarların sunucuda hesaplanması, callback sonucu API'den sorgulanıp imza/tutar doğrulaması ve tekrar işlem koruması gerekir. Anahtarlar kaynak koduna, public settings API'sine veya localStorage'a konulmamalıdır.
- Sandbox başarılı/başarısız/iptal ve tekrarlı callback testleri sonrasında canlı işlem testi yapılmalıdır.
- Üretim HTTPS sertifikası barındırma katmanında doğrulanmalıdır; sayfa metni veya logo sertifika sağlamaz.

Mevcut kart/OTP simülasyonu ödeme onayı oluşturamaz. Kart bilgisi toplanmaz. Havale bildirimleri PENDING / PENDING_PAYMENT olarak kaydedilir; banka tahsilatı doğrulanmadan PAID sayılmaz. Resmi hesap sahibi adı sitede yayımlanmadığından, bankanın alıcı adı zorunlu olduğu transferlerde müşteriler destek hattına başvurmalıdır.
