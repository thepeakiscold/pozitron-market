# PayTR hazırlığı — 20 Ekim 2026

Resmi kaynaklar:
- https://www.paytr.com/destek-merkezi/basvuru
- https://www.paytr.com/on-bilgilendirme (10.2–10.3)
- https://dev.paytr.com/iframe-api/iframe-api-1-adim
- https://dev.paytr.com/iframe-api/iframe-api-2-adim

Gizlilik, mesafeli satış, teslimat/iade, Hakkımızda ve İletişim sayfaları hazırlandı. PayTR resmi görseli ve PayTR sitesine bağlantı ödeme alanına eklendi. Logolar ödeme onayı anlamına gelmez; kart ödeme seçeneği yakında olarak gösterilir ve tahsilat başlatmaz.

Şahıs işletmesi belgelerinin kesin listesi PayTR tarafından başvurudan sonra iletilir. Başvuruda gerçek işletme sahibi bilgisi, vergi levhası, istenen imza/kimlik/ikamet belgeleri ve işletmeye ait IBAN sunulmalıdır. Sitede Ltd. ibaresi kullanılmaz. Kişisel adların sitede gösterilmemesi kullanıcı tercihidir; satıcı kimliği gerekliliğinin karşılandığı iddia edilmez.

Başvuru onayı ve Merchant ID/Key/Salt sağlanmadı. Anahtarlar yalnızca sunucu ortamında tutulmalıdır. Token sunucuda oluşturulmalı, ödeme sonucu bildirim URL'sinde HMAC/hash ve tutar doğrulanmalı; merchant_oid için tekrarlı bildirimin çift sipariş veya çift stok düşümü oluşturmaması sağlanmalıdır. Başarı dönüş sayfası tek başına ödeme kanıtı değildir.

PayTR sözleşmesindeki hizmet sağlayıcı duyurusu, hizmet gerçekten devreye alındığında ödeme alanında etkinleştirilmelidir. Şu an hizmet aktif olmadığı için yanlış bir aktif hizmet iddiası yayımlanmadı. Logo yerleşimi üretime geçişte PayTR'nin işyerine verdiği talimatla doğrulanmalıdır.
