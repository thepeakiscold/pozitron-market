# iyzico başvurusu için yapılan hazırlık

20 Ekim 2026 tarihinde resmi gereklilikler incelendi:
https://www.iyzico.com/isim-icin/sanal-pos
https://docs.iyzico.com/ek-bilgiler/iyzico-logo-paketi
https://docs.iyzico.com/odeme-metotlari/odeme-formu

Hakkımızda, iletişim, gizlilik, mesafeli satış, teslimat ve iade sayfaları erişilebilir. Görseldeki VKN, vergi dairesi ve kayıtlı adres kullanıldı. Gerçekliği doğrulanamayan limited şirket, sicil, MERSİS, KEP ve teknopark iddiaları kaldırıldı. Banka hesabı yeni IBAN ile güncellendi; yalnızca bir hesap gösterilir. IBAN uzunluğu ve MOD97 kontrolü geçerlidir; bu kontrol hesap sahipliğini doğrulamaz.

## Tamamlanmayı bekleyenler

- Kullanıcı kişisel adların yayımlanmamasını açıkça istedi. Şahıs işletmesinin resmi satıcı adı bu nedenle yayımlanmıyor. iyzico'nun satıcı kimliği şartı tam karşılanmış değildir; isim gizleme tercihi ile başvuru gerekliliği birlikte çözülmelidir.
- KEP ve varsa MERSİS/sicil/meslek odası bilgileri sağlanmadı. Uydurma kayıtlar eklenmedi.
- iyzico başvuru onayı ve işletme belgelerinin durumu işyeri panelinden doğrulanmadı. Sunucu entegrasyonu aşağıdaki bölümde anlatılmıştır; gerçek karttan tahsilat yapılmadı.
- CheckoutForm başlatma, sunucu tutar hesabı, API sorgulama, imza/tutar doğrulaması ve tekrar işlem koruması eklendi. Anahtarlar kaynak koduna, public settings API'sine veya localStorage'a konulmamalıdır.
- Sandbox başarılı/başarısız/iptal ve tekrarlı callback testleri sonrasında canlı işlem testi yapılmalıdır.
- Üretim HTTPS sertifikası barındırma katmanında doğrulanmalıdır; sayfa metni veya logo sertifika sağlamaz.

Mevcut kart/OTP simülasyonu ödeme onayı oluşturamaz. Kart bilgisi toplanmaz. Havale bildirimleri PENDING / PENDING_PAYMENT olarak kaydedilir; banka tahsilatı doğrulanmadan PAID sayılmaz. Resmi hesap sahibi adı sitede yayımlanmadığından, bankanın alıcı adı zorunlu olduğu transferlerde müşteriler destek hattına başvurmalıdır.


## Canlı CheckoutForm entegrasyonu — 20 Ekim 2026

- Sabit 1 TL deneme linki sepet ödeme akışında kullanılmaz. Her sipariş için sunucudaki güncel ürün fiyatları ve kupon kurallarıyla ayrı TRY oturumu oluşturulur; kargo, indirim sonrası 1.500 TL altında 99 TL'dir. Yönlendirmeden önce kesin tutar müşteriye gösterilir. Tek çekim sunulur.
- Sunucu ortamı: `IYZICO_API_KEY`, `IYZICO_SECRET_KEY`; isteğe bağlı `IYZICO_API_BASE` (varsayılan `https://api.iyzipay.com`). Anahtarlar yalnızca `/etc/pozitron/pozitron.env` üzerinde tutulur; Git, public settings ve tarayıcı depolarına yazılmaz.
- POST `/api/iyzico/initialize`: teslimat, fatura, sepet, sözleşme onayı ve gerçek alıcı kimliği gerekir. İstemci fiyatı, ödeme durumu ve kullanıcı kimliği güvenilir kabul edilmez. Kullanıcı kimliği yalnızca doğrulanmış Authorization tokenından alınır. IP başına dakikada beş başlangıç denemesi sınırı vardır.
- Alıcı kimlik numarası iyzico'ya iletilir; bu ödeme alanından gelen değer DB'ye veya localStorage'a kaydedilmez. Ayrı fatura alanlarının yasal saklanması farklıdır. Kart bilgileri sadece iyzico'nun HTTPS ortak ödeme sayfasında girilir.
- POST `/api/iyzico/callback`: form-urlencoded token kabul edilir; token tek başına ödeme kanıtı değildir. Sonuç iyzico API'sinden sorgulanır ve HMAC yanıt imzası, token, conversationId, basketId, TRY para birimi, price ve paidPrice doğrulanır. fraudStatus=1 ve SUCCESS dışındaki sonuçlar sevkiyatı başlatmaz.
- `iyzico_sessions` tablosu token, sipariş kimliği, ayrı rastgele sonuç anahtarı, kupon ve kontrol zamanını saklar. Sonuç sayfası yalnızca tahmin edilemez sonuç anahtarıyla sipariş numarası, tutar ve durumu okur; kişisel bilgiler gösterilmez.
- Ödenmemiş oturumlar stok/kupon tüketmez. Başarılı tahsilatta stok ve kupon tek SQLite işlemi içinde güncellenir. Tekrarlı callback stok veya kuponu tekrar tüketmez. Stok/kupon yarışında tahsilat PAID olarak kaydedilir, sipariş PAYMENT_REVIEW olur; operatör tedarik veya iade için müdahale etmelidir.
- Dakikada bir arka plan mutabakatı son yedi gündeki PENDING oturumları yeniden sorgular; callback kaybı ve iyzico inceleme sonuçları için yeniden başlatmadan sonra da devam eder. Yedi günü aşan belirsiz ödemeler işyeri panelinden manuel kontrol edilmelidir.
- `payment-result.html` müşteriye doğrulanmış sonucu gösterir. Başlatma, hata, ödeme sayfasının açılması veya tarayıcı dönüşü PAID kanıtı sayılmaz. Eski kart/OTP simülasyonu kapalıdır; PayTR entegrasyonu bu değişiklik kapsamında açılmaz.
- Testler sahte provider yanıtlarıyla çalışır. Anahtar doğrulaması var olmayan token sorgusuyla tahsilat oluşturmadan yapılır. Gerçek kartla uçtan uca canlı tahsilat testi yapılmadı; bunun başarılı olduğu iddia edilmemelidir. Eski başvuru ve resmi satıcı kimliği eksikleri bu teknik değişiklikle çözülmüş sayılmaz.

Resmi protokol kaynakları:
https://docs.iyzico.com/odeme-metotlari/odeme-formu/cf-entegrasyonu/cf-baslatma
https://docs.iyzico.com/ek-servisler/imza-yanitinin-dogrulanmasi
https://github.com/iyzico/iyzipay-python/blob/master/samples/retrieve_checkout_form_result.py
