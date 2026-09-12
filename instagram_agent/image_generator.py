import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'assets', 'instagram', 'posts')
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT_CANDIDATES_BOLD = [
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
]

FONT_CANDIDATES_REG = [
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
]

def get_font(size: int, bold: bool = False):
    candidates = FONT_CANDIDATES_BOLD if bold else FONT_CANDIDATES_REG
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

class ImageGenerator:
    def __init__(self, width: int = 1080, height: int = 1080):
        self.width = width
        self.height = height

    def generate_post_image(self, post_data: dict) -> str:
        """
        Creates a 1080x1080 high-res graphic and returns the relative image path.
        """
        post_id = post_data['id']
        content_type = post_data.get('content_type', 'product_spotlight')
        prod = post_data.get('product_data')
        tool_info = post_data.get('tool_info')

        img = Image.new('RGB', (self.width, self.height), color=(11, 15, 25))
        draw = ImageDraw.Draw(img)

        # Draw tech gradient background
        self._draw_background(img, draw)

        # Draw Top Branding Bar
        self._draw_header(draw, content_type)

        # Center Content Area
        if content_type in ('product_spotlight', 'review_highlight') and prod:
            self._draw_product_card(img, draw, prod)
        else:
            self._draw_tool_or_tip_card(img, draw, post_data)

        # Bottom CTA Footer Bar
        self._draw_footer(draw)

        # Save to disk
        filename = f"{post_id}.jpg"
        file_path = os.path.join(OUTPUT_DIR, filename)
        img.save(file_path, format='JPEG', quality=92, optimize=True)

        return f"./assets/instagram/posts/{filename}"

    def _draw_background(self, img: Image, draw: ImageDraw.Draw):
        # Layered dark gradient with cyan/blue accents
        for y in range(self.height):
            ratio = y / self.height
            # Deep carbon navy: (11, 15, 25) to (18, 27, 46)
            r = int(11 + (18 - 11) * ratio)
            g = int(15 + (27 - 15) * ratio)
            b = int(25 + (46 - 25) * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Top corner cyber glow
        glow = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse([(-100, -100), (380, 380)], fill=(2, 132, 199, 45))
        glow_draw.ellipse([(self.width - 300, self.height - 300), (self.width + 100, self.height + 100)], fill=(6, 182, 212, 35))
        glow = glow.filter(ImageFilter.GaussianBlur(80))
        img.paste(glow, (0, 0), glow)

        # Subtle cyber grid lines
        grid_color = (255, 255, 255, 6)
        grid_img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(grid_img)
        step = 60
        for x in range(0, self.width, step):
            g_draw.line([(x, 0), (x, self.height)], fill=grid_color)
        for y in range(0, self.height, step):
            g_draw.line([(0, y), (self.width, y)], fill=grid_color)
        img.paste(grid_img, (0, 0), grid_img)

    def _draw_header(self, draw: ImageDraw.Draw, content_type: str):
        # Pozitron Pill
        draw.rounded_rectangle([(60, 50), (370, 105)], radius=12, fill=(15, 23, 42), outline=(30, 41, 59), width=2)
        # Logo text
        font_logo = get_font(28, bold=True)
        draw.text((78, 62), "⚡ POZITRON", fill=(248, 250, 252), font=font_logo)
        draw.text((254, 62), ".MARKET", fill=(2, 132, 199), font=font_logo)

        # Right-side Category Tag
        type_labels = {
            'product_spotlight': '🛸 PRO FPV DONANIM',
            'tool_showcase': '🛠️ ONLİNE DRONE ARAÇLARI',
            'deal_drop': '🔥 HAFTANIN KAMPANYASI',
            'pilot_tip': '💡 FPV PİLOT AKADEMİSİ',
            'review_highlight': '⭐ DOĞRULANMIŞ PİLOT YORUMU'
        }
        tag_text = type_labels.get(content_type, '🛸 FPV DONANIM')
        font_tag = get_font(20, bold=True)
        draw.rounded_rectangle([(self.width - 390, 50), (self.width - 60, 105)], radius=12, fill=(2, 132, 199, 50), outline=(2, 132, 199), width=2)
        draw.text((self.width - 370, 66), tag_text, fill=(56, 189, 248), font=font_tag)

    def _draw_product_card(self, img: Image, draw: ImageDraw.Draw, prod: dict):
        # Outer Card
        card_box = [(60, 135), (self.width - 60, 930)]
        draw.rounded_rectangle(card_box, radius=24, fill=(15, 23, 42), outline=(30, 58, 95), width=2)

        # Inner Product Photo Container
        photo_box = [(90, 160), (self.width - 90, 640)]
        draw.rounded_rectangle(photo_box, radius=18, fill=(248, 250, 252))

        # Brand Badge inside photo
        brand = prod.get('brand', 'Pozitron')
        font_brand = get_font(22, bold=True)
        draw.rounded_rectangle([(110, 180), (110 + len(brand) * 16 + 40, 226)], radius=8, fill=(15, 23, 42))
        draw.text((125, 190), brand.upper(), fill=(255, 255, 255), font=font_brand)

        # Discount Badge if available
        discount = prod.get('discount_pct', 0)
        if discount and discount > 0:
            font_disc = get_font(22, bold=True)
            disc_w = 170
            draw.rounded_rectangle([(self.width - 110 - disc_w, 180), (self.width - 110, 226)], radius=8, fill=(220, 38, 38))
            draw.text((self.width - 110 - disc_w + 14, 190), f"-%{discount} İNDİRİM", fill=(255, 255, 255), font=font_disc)

        # Load & Paste Product Image
        img_url = prod.get('image_url', '')
        if img_url:
            clean_rel_path = img_url.lstrip('./').replace('/', os.sep)
            local_prod_img_path = os.path.join(BASE_DIR, clean_rel_path)
            if os.path.exists(local_prod_img_path):
                try:
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        prod_img = Image.open(local_prod_img_path).convert('RGBA')
                        # Fit within 750x420
                        max_w, max_h = 740, 420
                        prod_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                        # Center
                        paste_x = int(90 + (photo_box[1][0] - 90 - prod_img.width) / 2)
                        paste_y = int(170 + (photo_box[1][1] - 170 - prod_img.height) / 2)
                        img.paste(prod_img, (paste_x, paste_y), prod_img)
                except Exception:
                    pass

        # Product Name
        name = prod.get('name_tr') or prod.get('name_en', 'Pozitron FPV Component')
        font_title = get_font(34, bold=True)
        # Wrap if title is too long
        if len(name) > 42:
            title_line1 = name[:40] + "..."
        else:
            title_line1 = name
        draw.text((95, 665), title_line1, fill=(255, 255, 255), font=font_title)

        # Technical Feature Pills
        specs = {}
        try:
            import json
            specs = json.loads(prod.get('specs_json', '{}'))
        except Exception:
            specs = {}

        pills = []
        for k, v in list(specs.items())[:3]:
            val_str = str(v)[:14]
            pills.append(f"{k}: {val_str}")
        if not pills:
            pills = ["Garantili Orijinal", "Yüksek Performans", "FPV Standart"]

        pill_x = 95
        font_pill = get_font(18, bold=False)
        for pill_text in pills:
            pill_w = len(pill_text) * 10 + 26
            draw.rounded_rectangle([(pill_x, 725), (pill_x + pill_w, 765)], radius=6, fill=(30, 41, 59), outline=(51, 65, 85), width=1)
            draw.text((pill_x + 12, 734), pill_text, fill=(203, 213, 225), font=font_pill)
            pill_x += pill_w + 12

        # Price Area
        price_try = prod.get('price_try', 0.0)
        price_usd = prod.get('price_usd', 0.0)
        font_price = get_font(44, bold=True)
        draw.text((95, 810), f"{price_try:,.2f} ₺", fill=(34, 197, 94), font=font_price)

        font_usd = get_font(24, bold=True)
        draw.text((95, 870), f"(${price_usd:.2f} USD)", fill=(148, 163, 184), font=font_usd)

        # Stock / Delivery Badge Right
        draw.rounded_rectangle([(self.width - 390, 825), (self.width - 95, 885)], radius=12, fill=(2, 132, 199))
        font_btn = get_font(22, bold=True)
        draw.text((self.width - 370, 842), "⚡ AYNI GÜN HIZLI KARGO", fill=(255, 255, 255), font=font_btn)

    def _draw_tool_or_tip_card(self, img: Image, draw: ImageDraw.Draw, post_data: dict):
        card_box = [(60, 135), (self.width - 60, 930)]
        draw.rounded_rectangle(card_box, radius=24, fill=(15, 23, 42), outline=(30, 58, 95), width=2)

        tool_info = post_data.get('tool_info', {})
        badge_text = tool_info.get('badge', 'POZITRON ÖZEL')
        headline = tool_info.get('headline', post_data.get('title', 'FPV REHBERİ'))
        subhead = tool_info.get('subhead', 'Pozitron Market Uzman Ekibi')

        # Badge
        font_b = get_font(24, bold=True)
        draw.rounded_rectangle([(100, 180), (100 + len(badge_text) * 16 + 40, 236)], radius=10, fill=(2, 132, 199))
        draw.text((120, 194), badge_text, fill=(255, 255, 255), font=font_b)

        # Big Headline
        font_hl = get_font(46, bold=True)
        lines = self._wrap_text(headline, 28)
        y = 270
        for l in lines[:2]:
            draw.text((100, y), l, fill=(255, 255, 255), font=font_hl)
            y += 58

        # Subhead
        font_sub = get_font(28, bold=False)
        sub_lines = self._wrap_text(subhead, 44)
        for sl in sub_lines[:2]:
            draw.text((100, y + 10), sl, fill=(148, 163, 184), font=font_sub)
            y += 42

        # Illustrative Box / Graphic Mockup in Center
        y_box = y + 30
        box_rect = [(100, y_box), (self.width - 100, 770)]
        draw.rounded_rectangle(box_rect, radius=16, fill=(30, 41, 59), outline=(51, 65, 85), width=2)

        # Feature highlights inside box
        content_type = post_data.get('content_type')
        items = []
        if content_type == 'tool_showcase':
            items = [
                "✅ Motor KV ve 4S / 6S Pil Voltajını Anında Eşleştir",
                "✅ ESC Amper Sınırını Otomatik Hesapla & Doğrula",
                "✅ Tek Tıkla Parça Listesini WhatsApp / Link Olarak Paylaş",
                "✅ %100 Ücretsiz Mühendislik & Uyumluluk Aracı"
            ]
        elif content_type == 'deal_drop':
            code = tool_info.get('coupon_code', 'POZITRON10')
            items = [
                f"🏷️ Aktif Kupon Kodu: {code}",
                "🎁 Sepette Anında İndirim",
                "📦 Tüm Motor, ESC, FC ve Parçalarda Geçerli",
                "⏱️ Stoklarla Sınırlı Süper Fırsat"
            ]
        else: # pilot_tip
            items = [
                "⚡ Motor ve ESC Yanmalarını Engelleyen Doğru Kombinasyon",
                "🔋 LiPo Pil Ömrünü 3 Kat Uzatan Şarj Kuralları",
                "🛠️ Titreşimsiz HD Görüntü İçin PID & Filtre İpuçları",
                "🚀 Pozitron FPV Topluluğuna Katılın!"
            ]

        font_item = get_font(26, bold=True)
        item_y = y_box + 40
        for it in items:
            draw.text((130, item_y), it, fill=(241, 245, 249), font=font_item)
            item_y += 65

        # Call to Action Button
        draw.rounded_rectangle([(100, 810), (self.width - 100, 885)], radius=14, fill=(2, 132, 199))
        font_action = get_font(30, bold=True)
        draw.text((self.width // 2 - 270, 832), "👉 PROFİLDEKİ LİNKTEN HEMEN DENE 👈", fill=(255, 255, 255), font=font_action)

    def _draw_footer(self, draw: ImageDraw.Draw):
        # Footer text
        font_foot = get_font(20, bold=True)
        foot_text = "🌐 pozitronmarket.com   |   📱 @pozitronmarket   |   ⚡ Türkiye'nin FPV Donanım Pazarı"
        draw.text((140, 995), foot_text, fill=(100, 116, 139), font=font_foot)

    def _wrap_text(self, text: str, max_chars: int) -> list:
        words = text.split()
        lines = []
        current = []
        curr_len = 0
        for w in words:
            if curr_len + len(w) + 1 <= max_chars:
                current.append(w)
                curr_len += len(w) + 1
            else:
                if current:
                    lines.append(" ".join(current))
                current = [w]
                curr_len = len(w)
        if current:
            lines.append(" ".join(current))
        return lines
