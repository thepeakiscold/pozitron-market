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

def clean_canvas_text(text: str) -> str:
    """Removes unsupported unicode emojis that render as missing boxes on Linux fonts."""
    if not text:
        return ""
    replacements = {
        '⚡': ' ', '🛸': ' ', '📝': ' ', '📦': ' ', '🎯': ' ',
        '🔥': ' ', '🛡️': ' ', '🛠️': ' ', '🔋': ' ', '⏱️': ' ',
        '✅': ' ', '🏷️': ' ', '⭐': '★', '💬': ' ', '👉': ' ',
        '👈': ' ', '👆': ' ', '👇': ' ', '₺': 'TL', '🦾': ' ',
        '💥': ' ', '🚀': ' ', '⚙️': ' ', '🔗': ' '
    }
    for em, sym in replacements.items():
        text = text.replace(em, sym)
    import re
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    return " ".join(text.split())

def _load_product_image(local_path: str):
    """Loads product image with AVIF and ffmpeg fallback."""
    if not os.path.exists(local_path):
        return None
    try:
        import pillow_avif
    except Exception:
        pass
    try:
        return Image.open(local_path).convert('RGBA')
    except Exception:
        pass
    # Fallback via ffmpeg
    try:
        import subprocess
        tmp_png = f"/tmp/pztr_prod_{os.getpid()}.png"
        res = subprocess.run(['ffmpeg', '-i', local_path, tmp_png, '-y', '-loglevel', 'quiet'], timeout=6)
        if res.returncode == 0 and os.path.exists(tmp_png):
            im = Image.open(tmp_png).convert('RGBA')
            os.remove(tmp_png)
            return im
    except Exception:
        pass
    return None

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
        visual_summary = post_data.get('visual_summary') or {}
        if content_type in ('product_spotlight', 'review_highlight') and prod:
            self._draw_product_card(img, draw, prod, visual_summary)
        else:
            self._draw_tool_or_tip_card(img, draw, post_data, visual_summary)

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
        
        # Cyber Lightning bolt vector icon
        bolt = [(80, 80), (88, 62), (83, 74), (94, 74), (82, 95), (86, 81)]
        draw.polygon(bolt, fill=(56, 189, 248))
        
        font_logo = get_font(28, bold=True)
        draw.text((102, 62), "POZITRON", fill=(248, 250, 252), font=font_logo)
        draw.text((254, 62), ".MARKET", fill=(2, 132, 199), font=font_logo)

        # Right-side Category Tag
        type_labels = {
            'product_spotlight': 'PRO FPV DONANIM',
            'tool_showcase': 'ONLINE DRONE ARACLARI',
            'deal_drop': 'HAFTANIN KAMPANYASI',
            'pilot_tip': 'FPV PILOT AKADEMISI',
            'review_highlight': 'DOGRULANMIS PILOT YORUMU'
        }
        tag_text = type_labels.get(content_type, 'PRO FPV DONANIM')
        font_tag = get_font(20, bold=True)
        draw.rounded_rectangle([(self.width - 390, 50), (self.width - 60, 105)], radius=12, fill=(2, 132, 199, 50), outline=(2, 132, 199), width=2)
        draw.text((self.width - 370, 66), tag_text, fill=(56, 189, 248), font=font_tag)

    def _draw_product_card(self, img: Image, draw: ImageDraw.Draw, prod: dict, visual_summary: dict = None):
        if visual_summary is None:
            visual_summary = {}

        # Outer Card
        card_box = [(60, 130), (self.width - 60, 935)]
        draw.rounded_rectangle(card_box, radius=24, fill=(15, 23, 42), outline=(30, 58, 95), width=2)

        # Inner Product Photo Container
        photo_box = [(90, 150), (self.width - 90, 545)]
        draw.rounded_rectangle(photo_box, radius=18, fill=(248, 250, 252))

        # Brand Badge inside photo
        brand = clean_canvas_text(prod.get('brand', 'Pozitron'))
        font_brand = get_font(22, bold=True)
        draw.rounded_rectangle([(110, 168), (110 + len(brand) * 16 + 40, 214)], radius=8, fill=(15, 23, 42))
        draw.text((125, 178), brand.upper(), fill=(255, 255, 255), font=font_brand)

        # Discount Badge if available
        discount = prod.get('discount_pct', 0)
        if discount and discount > 0:
            font_disc = get_font(22, bold=True)
            disc_w = 170
            draw.rounded_rectangle([(self.width - 110 - disc_w, 168), (self.width - 110, 214)], radius=8, fill=(220, 38, 38))
            draw.text((self.width - 110 - disc_w + 14, 178), f"-%{discount} INDIRIM", fill=(255, 255, 255), font=font_disc)

        # Load & Paste Product Image
        img_url = prod.get('image_url', '')
        if img_url:
            clean_rel_path = img_url.lstrip('./').replace('/', os.sep)
            local_prod_img_path = os.path.join(BASE_DIR, clean_rel_path)
            prod_img = _load_product_image(local_prod_img_path)
            if prod_img:
                try:
                    max_w, max_h = 720, 370
                    prod_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                    paste_x = int(90 + (photo_box[1][0] - 90 - prod_img.width) / 2)
                    paste_y = int(150 + (photo_box[1][1] - 150 - prod_img.height) / 2)
                    img.paste(prod_img, (paste_x, paste_y), prod_img)
                except Exception:
                    pass

        # Product Name
        name = clean_canvas_text(prod.get('name_tr') or prod.get('name_en', 'Pozitron FPV Component'))
        font_title = get_font(32, bold=True)
        if len(name) > 42:
            title_line1 = name[:40] + "..."
        else:
            title_line1 = name
        draw.text((95, 560), title_line1, fill=(255, 255, 255), font=font_title)

        # Visual Summary of Post Text (Gemini AI Summary Points)
        points = visual_summary.get('key_points', [])
        if not points:
            points = [
                f"Orijinal {brand} Guvencesi & Dayanikli Govde",
                "Yuksek Hassasiyet & Yaris / Freestyle Uyumlulugu"
            ]

        # Draw Visual Summary Box
        summary_box = [(90, 610), (self.width - 90, 780)]
        draw.rounded_rectangle(summary_box, radius=14, fill=(20, 29, 45), outline=(30, 58, 95), width=2)
        
        # Summary Header
        font_hdr = get_font(18, bold=True)
        draw.text((115, 622), "• GONDERI OZETI & ONE CIKAN NOKTALAR", fill=(56, 189, 248), font=font_hdr)
        draw.line([(115, 646), (self.width - 115, 646)], fill=(30, 41, 59), width=1)

        font_pt = get_font(21, bold=True)
        y_pt = 658
        for pt in points[:3]:
            clean_pt = clean_canvas_text(pt)
            draw.text((115, y_pt), f"•  {clean_pt[:58]}", fill=(241, 245, 249), font=font_pt)
            y_pt += 36

        # Price Area (Bottom Left)
        price_try = prod.get('price_try', 0.0)
        price_usd = prod.get('price_usd', 0.0)
        font_price = get_font(42, bold=True)
        draw.text((95, 805), f"{price_try:,.2f} TL", fill=(34, 197, 94), font=font_price)

        font_usd = get_font(22, bold=True)
        draw.text((95, 860), f"(${price_usd:.2f} USD)", fill=(148, 163, 184), font=font_usd)

        # Stock / Delivery Badge (Bottom Right)
        draw.rounded_rectangle([(self.width - 390, 818), (self.width - 95, 878)], radius=12, fill=(2, 132, 199))
        font_btn = get_font(22, bold=True)
        draw.text((self.width - 370, 835), "AYNI GUN HIZLI KARGO", fill=(255, 255, 255), font=font_btn)

    def _draw_tool_or_tip_card(self, img: Image, draw: ImageDraw.Draw, post_data: dict, visual_summary: dict = None):
        if visual_summary is None:
            visual_summary = post_data.get('visual_summary') or {}

        card_box = [(60, 130), (self.width - 60, 935)]
        draw.rounded_rectangle(card_box, radius=24, fill=(15, 23, 42), outline=(30, 58, 95), width=2)

        badge_text = clean_canvas_text(visual_summary.get('badge') or 'POZITRON REHBERI')
        headline = clean_canvas_text(visual_summary.get('headline') or post_data.get('title', 'FPV REHBERI'))
        subhead = clean_canvas_text(visual_summary.get('subhead') or 'Pozitron Market Uzman Ekibi')

        # Badge
        font_b = get_font(24, bold=True)
        badge_w = len(badge_text) * 15 + 40
        draw.rounded_rectangle([(95, 165), (95 + badge_w, 218)], radius=10, fill=(2, 132, 199))
        draw.text((115, 178), badge_text, fill=(255, 255, 255), font=font_b)

        # Big Headline
        font_hl = get_font(44, bold=True)
        lines = self._wrap_text(headline, 28)
        y = 245
        for l in lines[:2]:
            draw.text((95, y), l, fill=(255, 255, 255), font=font_hl)
            y += 54

        # Subhead
        font_sub = get_font(26, bold=False)
        sub_lines = self._wrap_text(subhead, 44)
        for sl in sub_lines[:2]:
            draw.text((95, y + 6), sl, fill=(148, 163, 184), font=font_sub)
            y += 38

        # Center Visual Summary Box
        y_box = y + 25
        box_rect = [(95, y_box), (self.width - 95, 785)]
        draw.rounded_rectangle(box_rect, radius=18, fill=(24, 33, 47), outline=(30, 58, 95), width=2)

        # Header inside Box
        font_box_hdr = get_font(20, bold=True)
        draw.text((125, y_box + 20), "• GONDERI OZETI & ONEMLI NOKTALAR", fill=(56, 189, 248), font=font_box_hdr)
        draw.line([(125, y_box + 50), (self.width - 125, y_box + 50)], fill=(30, 41, 59), width=1)

        # Feature highlights inside box (Visual summary points)
        items = visual_summary.get('key_points', [])
        if not items:
            items = [
                "Motor, ESC ve Pil Uyumlulugunu Kolayca Eslestirin",
                "Pozitron Market Guvencesiyle En Dogru FPV Parcalari",
                "Orijinal Urun ve Hizli Teknik Destek"
            ]

        font_item = get_font(24, bold=True)
        item_y = y_box + 70
        for it in items[:4]:
            clean_it = clean_canvas_text(it)
            draw.text((125, item_y), f"•  {clean_it[:58]}", fill=(241, 245, 249), font=font_item)
            item_y += 54

        # Call to Action Button
        cta_text = clean_canvas_text(visual_summary.get('cta', '> PROFILDEKI LINKTEN HEMEN KESFET <'))
        draw.rounded_rectangle([(95, 818), (self.width - 95, 888)], radius=14, fill=(2, 132, 199))
        font_action = get_font(28, bold=True)
        btn_w = len(cta_text) * 15
        btn_x = max(115, (self.width - btn_w) // 2)
        draw.text((btn_x, 836), cta_text, fill=(255, 255, 255), font=font_action)

    def _draw_footer(self, draw: ImageDraw.Draw):
        # Footer text
        font_foot = get_font(20, bold=True)
        foot_text = "pozitronmarket.com   |   @pozitronmarket   |   Turkiye'nin FPV Donanim Pazari"
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
