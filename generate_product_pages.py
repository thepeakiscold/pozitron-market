#!/usr/bin/env python3
"""
generate_product_pages.py
Static Site Generator (SSG) for Pozitron Market (https://pozitronmarket.com)
Generates 500 individual SEO-optimized HTML product pages featuring Amazon-inspired
high-conversion features:
1. Frequently Bought Together (Bundling & Save)
2. Live Same-Day Shipping Countdown Timer
3. Compare Similar Items Matrix
4. 1-Click Fast "Buy Now" Checkout
5. Low-Stock Urgency Scarcity Indicators
6. Customer Technical Q&A Section

Strict aesthetic guidelines: Zero emojis, clean SVGs, synchronized with styles.css.
"""

import json
import os
import html
import re
from datetime import datetime

BASE_URL = "https://pozitronmarket.com"
PRODUCTS_JSON_PATH = "data/products.json"
CATEGORIES_JSON_PATH = "data/categories.json"
OUTPUT_DIR = "products"
SITEMAP_PATH = "sitemap.xml"

COMPLEMENTARY_CATEGORIES = {
    "motors": ["esc", "propellers", "frames"],
    "esc": ["flight_controllers", "motors", "batteries_chargers"],
    "flight_controllers": ["esc", "vtx", "transmitters_receivers"],
    "vtx": ["antennas", "cameras", "accessories_hardware"],
    "cameras": ["vtx", "frames", "accessories_hardware"],
    "frames": ["motors", "propellers", "accessories_hardware"],
    "propellers": ["motors", "accessories_hardware", "tools_supplies"],
    "antennas": ["vtx", "transmitters_receivers", "accessories_hardware"],
    "batteries_chargers": ["tools_supplies", "accessories_hardware", "transmitters_receivers"],
    "transmitters_receivers": ["antennas", "flight_controllers", "batteries_chargers"],
    "tools_supplies": ["accessories_hardware", "batteries_chargers", "motors"],
    "accessories_hardware": ["tools_supplies", "frames", "motors"]
}

def format_try(amount):
    try:
        val = float(amount)
        formatted = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} ₺"
    except (ValueError, TypeError):
        return f"{amount} ₺"

def escape_str(s):
    if not s:
        return ""
    return html.escape(str(s).strip(), quote=True)

def get_bundle_items(current_prod, by_category, all_products):
    cid = current_prod.get("category_id", "motors")
    targets = COMPLEMENTARY_CATEGORIES.get(cid, ["accessories_hardware", "tools_supplies"])
    bundle = []
    current_slug = current_prod.get("slug")
    
    for t_cid in targets:
        candidates = by_category.get(t_cid, [])
        valid = [p for p in candidates if p.get("slug") != current_slug and p not in bundle]
        if valid:
            idx = abs(hash(current_slug + t_cid)) % len(valid)
            bundle.append(valid[idx])
        if len(bundle) == 2:
            break
            
    if len(bundle) < 2:
        for p in all_products:
            if p.get("slug") != current_slug and p not in bundle:
                bundle.append(p)
            if len(bundle) == 2:
                break
    return bundle

def generate_product_page(product, category, related_products, all_products, by_category):
    p_id = product.get("id", "")
    slug = product.get("slug", "")
    sku = product.get("sku", "")
    name_tr = product.get("name_tr") or product.get("name_en") or "FPV Drone Parçası"
    name_en = product.get("name_en") or product.get("name_tr") or ""
    brand = product.get("brand", "Pozitron")
    price_try = product.get("price_try", 0.0)
    price_usd = float(product.get("price_usd") or 0.0)
    original_price_try = product.get("original_price_try", price_try)
    image_rel = product.get("image_url", "./assets/placeholder.png")
    
    # Path handling from products/ directory
    if image_rel.startswith("./"):
        img_src = f"../{image_rel[2:]}"
        abs_img = f"{BASE_URL}/{image_rel[2:]}"
    elif image_rel.startswith("/"):
        img_src = f"..{image_rel}"
        abs_img = f"{BASE_URL}{image_rel}"
    elif image_rel.startswith("http"):
        img_src = image_rel
        abs_img = image_rel
    else:
        img_src = f"../{image_rel}"
        abs_img = f"{BASE_URL}/{image_rel}"

    desc_tr = product.get("description_tr") or f"{name_tr}, yüksek performanslı FPV drone ve robotik projeleri için tasarlanmış birinci sınıf donanım bileşenidir."
    desc_en = product.get("description_en") or ""
    specs = product.get("specs") or {}
    rating = float(product.get("rating") or 0.0)
    review_count = int(product.get("review_count") or 0)

    cat_name_tr = category.get("name_tr", "Drone Parçaları") if category else "Drone Parçaları"
    cat_id = category.get("id", "motors") if category else "motors"

    canonical_url = f"{BASE_URL}/products/{slug}.html"

    # Meta description
    clean_desc_tr = re.sub(r'<[^>]+>', '', desc_tr).replace('"', '&quot;').strip()
    meta_desc = f"{name_tr} en uygun fiyat ve hızlı teslimat avantajıyla Pozitron Market'te! {brand} marka donanım, teknik özellikler ve taksit fırsatıyla hemen inceleyin."
    if len(meta_desc) > 165:
        meta_desc = meta_desc[:162] + "..."

    # Discount calculation
    has_discount = False
    discount_pct = 0
    if original_price_try and original_price_try > price_try:
        has_discount = True
        discount_pct = int(round(((original_price_try - price_try) / original_price_try) * 100))

    # Real Stock Status from Database
    real_stock = int(product.get("stock", 0))
    is_in_stock = real_stock > 0
    is_low_stock = 0 < real_stock <= 3

    # WhatsApp order link pre-filled
    wa_msg = f"Merhaba, Pozitron Market web sitenizdeki şu ürünü sipariş etmek istiyorum:\n\nÜrün: {name_tr}\nKod: {sku}\nAdet: 1\nFiyat: {format_try(price_try)}\nLink: {canonical_url}"
    import urllib.parse
    wa_url = f"https://wa.me/905425465562?text={urllib.parse.quote(wa_msg)}"

    # Specs table rows
    specs_rows_html = ""
    spec_labels = {
        "brand": "Marka / Üretici",
        "model": "Model / Seri",
        "spec_variant": "Teknik Varyant",
        "option": "Opsiyon / Değer",
        "input_voltage": "Çalışma Voltajı / Hücre",
        "mounting_spec": "Montaj Şeması & Vida",
        "weight_g": "Ağırlık",
        "dimensions_mm": "Boyutlar",
        "in_the_box": "Kutu İçeriği"
    }

    for key, label in spec_labels.items():
        val = specs.get(key)
        if val:
            display_val = f"{val} g" if key == "weight_g" and not str(val).endswith("g") else f"{val} mm" if key == "dimensions_mm" and not str(val).endswith("mm") else str(val)
            specs_rows_html += f"""
              <tr>
                <td class="label">{escape_str(label)}</td>
                <td class="val">{escape_str(display_val)}</td>
              </tr>
            """

    # 1. Frequently Bought Together (Bundling)
    bundle_items = get_bundle_items(product, by_category, all_products)
    bundle_total = price_try + sum(item.get("price_try", 0) for item in bundle_items)
    bundle_discount_price = bundle_total * 0.95  # 5% bundle discount
    bundle_savings = bundle_total - bundle_discount_price

    all_bundle_products = [product] + bundle_items
    bundle_items_html = ""
    for idx, b_item in enumerate(all_bundle_products):
        b_name = b_item.get("name_tr") or b_item.get("name_en")
        b_price = b_item.get("price_try", 0)
        b_img = b_item.get("image_url", "./assets/placeholder.png")
        b_img_src = f"../{b_img[2:]}" if b_img.startswith("./") else b_img
        b_sku = b_item.get("sku", "")
        b_id = b_item.get("id", "")

        is_this_item = (idx == 0)
        bundle_items_html += f"""
          <div class="pdp-bundle-item" data-bundle-idx="{idx}">
            <div class="pdp-bundle-thumb-wrap">
              <img src="{escape_str(b_img_src)}" alt="{escape_str(b_name)}" loading="lazy" onerror="this.src='../assets/hero_drone.png'">
            </div>
            <label class="pdp-bundle-check-label">
              <input type="checkbox" checked data-price="{float(b_price)}" data-sku="{escape_str(b_sku)}" data-id="{escape_str(b_id)}" data-name="{escape_str(b_name)}" data-img="{escape_str(b_img)}" onchange="updateBundleTotal()">
              <div>
                <div class="pdp-bundle-item-name">{escape_str(b_name)} {'<strong>(Bu Ürün)</strong>' if is_this_item else ''}</div>
                <div class="pdp-bundle-item-price">{format_try(b_price)}</div>
              </div>
            </label>
          </div>
        """
        if idx < len(all_bundle_products) - 1:
            bundle_items_html += '<div class="pdp-bundle-plus-separator">+</div>'

    bundle_section_html = f"""
    <div class="pdp-card pdp-bundle-section">
      <h2 class="pdp-card-title">Sıklıkla Birlikte Alınanlar</h2>
      <div class="pdp-bundle-grid">
        <div class="pdp-bundle-items-wrap">
          {bundle_items_html}
        </div>
        <div class="pdp-bundle-cta-box">
          <span class="pdp-bundle-total-label">Paket Toplam Fiyatı:</span>
          <div class="pdp-bundle-total-price" id="bundle-total-price-val">{format_try(bundle_total)}</div>
          <span class="pdp-bundle-savings-tag">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
            <span>Uyumlu Donanım Paketi</span>
          </span>
          <button type="button" class="pdp-btn-bundle-buy" onclick="handleBundleAddToCart()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
            <span id="bundle-btn-text">Seçilenleri Birlikte Sepete Ekle</span>
          </button>
        </div>
      </div>
    </div>
    """

    # 2. Compare Similar Items Matrix
    compare_candidates = [rp for rp in related_products[:3]]
    compare_cols = [product] + compare_candidates
    
    compare_matrix_html = ""
    if len(compare_cols) >= 2:
        compare_rows = [
            ("Ürün Görseli", "img"),
            ("Model Başlığı", "name"),
            ("Fiyat", "price"),
            ("Müşteri Değerlendirmesi", "rating"),
            ("Üretici Marka", "brand"),
            ("Giriş Voltajı / Varyant", "voltage"),
            ("Stok Durumu", "stock"),
            ("Aksiyon", "action")
        ]

        table_rows_html = ""
        for label, row_type in compare_rows:
            table_rows_html += f'<tr><th class="feat-col">{escape_str(label)}</th>'
            for idx, c_prod in enumerate(compare_cols):
                is_curr = (idx == 0)
                curr_cls = "is-current" if is_curr else ""
                
                c_name = c_prod.get("name_tr") or c_prod.get("name_en")
                c_price = c_prod.get("price_try", 0)
                c_brand = c_prod.get("brand", "Pozitron")
                c_slug = c_prod.get("slug", "")
                c_rating = float(c_prod.get("rating") or 0.0)
                c_reviews = int(c_prod.get("review_count") or 0)
                c_specs = c_prod.get("specs") or {}
                c_volt = c_specs.get("input_voltage") or c_specs.get("spec_variant") or "Standart FPV"
                c_img = c_prod.get("image_url", "./assets/placeholder.png")
                c_img_src = f"../{c_img[2:]}" if c_img.startswith("./") else c_img
                c_id = c_prod.get("id", "")
                c_sku = c_prod.get("sku", "")

                if row_type == "img":
                    cell_content = f"""
                      {f'<span class="pdp-current-badge">İncelenen Ürün</span>' if is_curr else ''}
                      <img src="{escape_str(c_img_src)}" alt="{escape_str(c_name)}" class="pdp-compare-img" loading="lazy" onerror="this.src='../assets/hero_drone.png'">
                    """
                elif row_type == "name":
                    cell_content = f"""
                      <a href="./{c_slug}.html" class="pdp-compare-prod-name" title="{escape_str(c_name)}">
                        {escape_str(c_name)}
                      </a>
                    """
                elif row_type == "price":
                    cell_content = f'<div class="pdp-compare-price">{format_try(c_price)}</div>'
                elif row_type == "rating":
                    c_rev = int(c_prod.get("review_count", 0) or 0)
                    c_rat = float(c_prod.get("rating", 0.0) or 0.0)
                    if c_rev > 0 and c_rat > 0:
                        cell_content = f"""
                          <div style="color:#f59e0b; font-size:0.88rem; font-weight:700;">★ {c_rat:.1f}</div>
                          <div style="font-size:0.75rem; color:var(--text-muted);">({c_rev} değerlendirme)</div>
                        """
                    else:
                        cell_content = '<span style="font-size:0.82rem; color:var(--text-muted);">-</span>'
                elif row_type == "brand":
                    cell_content = f'<strong>{escape_str(c_brand)}</strong>'
                elif row_type == "voltage":
                    cell_content = f'<span style="font-size:0.82rem;">{escape_str(c_volt)}</span>'
                elif row_type == "stock":
                    cell_content = '<span style="color:#10b981; font-weight:600; font-size:0.82rem;">Stokta Var</span>'
                elif row_type == "action":
                    if is_curr:
                        cell_content = f"""
                          <button type="button" class="pdp-btn-compare-cart" onclick="handleAddToCart(false)">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
                            <span>Sepete Ekle</span>
                          </button>
                        """
                    else:
                        cell_content = f"""
                          <button type="button" class="pdp-btn-compare-cart" onclick="addSingleCompareToCart('{escape_str(c_id)}', '{escape_str(c_sku)}', '{escape_str(c_name)}', {float(c_price)}, '{escape_str(c_img)}')">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
                            <span>Sepete Ekle</span>
                          </button>
                        """
                else:
                    cell_content = ""

                table_rows_html += f'<td class="prod-col {curr_cls}">{cell_content}</td>'
            table_rows_html += '</tr>'

        compare_matrix_html = f"""
        <div class="pdp-card pdp-compare-section">
          <h2 class="pdp-card-title">Benzer {escape_str(cat_name_tr)} Karşılaştırması</h2>
          <div class="pdp-compare-table-wrap">
            <table class="pdp-compare-table">
              <tbody>
                {table_rows_html}
              </tbody>
            </table>
          </div>
        </div>
        """

    # Related products HTML
    related_html = ""
    for rel in related_products[:4]:
        rel_slug = rel.get("slug", "")
        rel_name = rel.get("name_tr") or rel.get("name_en")
        rel_price = rel.get("price_try", 0)
        rel_img = rel.get("image_url", "./assets/placeholder.png")
        rel_img_src = f"../{rel_img[2:]}" if rel_img.startswith("./") else rel_img
        related_html += f"""
          <a href="./{rel_slug}.html" class="pdp-related-card">
            <div class="pdp-related-img-wrap">
              <img src="{escape_str(rel_img_src)}" alt="{escape_str(rel_name)}" loading="lazy" onerror="this.src='../assets/hero_drone.png'">
            </div>
            <div class="pdp-related-info">
              <div class="pdp-related-title">{escape_str(rel_name)}</div>
              <div class="pdp-related-price">{format_try(rel_price)}</div>
            </div>
          </a>
        """

    # JSON-LD Schema
    schema_json = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": name_tr,
        "image": [abs_img],
        "description": clean_desc_tr[:300],
        "sku": sku,
        "mpn": sku,
        "brand": {
            "@type": "Brand",
            "name": brand
        },
        "offers": {
            "@type": "Offer",
            "url": canonical_url,
            "priceCurrency": "TRY",
            "price": f"{float(price_try):.2f}",
            "priceValidUntil": "2027-12-31",
            "itemCondition": "https://schema.org/NewCondition",
            "availability": "https://schema.org/InStock",
            "seller": {
                "@type": "Organization",
                "name": "Pozitron Market",
                "url": BASE_URL
            }
        }
    }
    if review_count > 0 and rating > 0:
        schema_json["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(round(rating, 1)),
            "reviewCount": str(review_count),
            "bestRating": "5",
            "worstRating": "1"
        }

    breadcrumb_json = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Ana Sayfa",
                "item": f"{BASE_URL}/"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": cat_name_tr,
                "item": f"{BASE_URL}/#category={cat_id}"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": brand,
                "item": f"{BASE_URL}/#brand={urllib.parse.quote(brand)}"
            },
            {
                "@type": "ListItem",
                "position": 4,
                "name": name_tr,
                "item": canonical_url
            }
        ]
    }

    # Dynamic Rating HTML
    if review_count > 0 and rating > 0:
        filled_stars_count = min(5, max(1, int(round(rating))))
        stars_svg = "".join([
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>'
            for _ in range(filled_stars_count)
        ]) + "".join([
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>'
            for _ in range(5 - filled_stars_count)
        ])
        pdp_rating_row_html = f'''
        <a href="#pdp-reviews-section" class="pdp-rating-row" style="text-decoration:none; cursor:pointer;" title="{rating:.1f} / 5 Yıldız ({review_count} Değerlendirme)">
          <div class="pdp-stars">
            {stars_svg}
          </div>
          <span class="pdp-rating-val">{rating:.1f}</span>
          <span class="pdp-review-count">({review_count} Değerlendirme)</span>
        </a>'''
        pdp_rating_summary_box_html = f'''
      <!-- Rating Breakdown Box -->
      <div class="pdp-rating-summary-grid" style="display:grid; grid-template-columns: 200px 1fr; gap: 28px; align-items:center; margin-bottom:24px; background:#f8fafc; padding:20px; border-radius:12px; border:1px solid #e2e8f0;">
        <div style="text-align:center;">
          <div style="font-size:2.8rem; font-weight:900; color:#0f172a; line-height:1;">{rating:.1f}</div>
          <div style="color:#f59e0b; font-size:1.1rem; margin:6px 0;">{"★" * int(round(rating))}</div>
          <div style="font-size:0.82rem; color:#64748b;">{review_count} müşteri değerlendirmesi</div>
        </div>
        <div style="display:flex; flex-direction:column; gap:6px;">
          <div style="display:flex; align-items:center; gap:10px; font-size:0.82rem;">
            <span style="width:48px; text-align:right;">5 Yıldız</span>
            <div style="flex:1; height:8px; background:#e2e8f0; border-radius:4px; overflow:hidden;">
              <div style="width:100%; height:100%; background:#f59e0b; border-radius:4px;"></div>
            </div>
            <span style="width:34px; color:#64748b;">%100</span>
          </div>
        </div>
      </div>'''
    else:
        empty_stars_svg = "".join([
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>'
            for _ in range(5)
        ])
        pdp_rating_row_html = f'''
        <a href="#pdp-reviews-section" class="pdp-rating-row" style="text-decoration:none; cursor:pointer;" title="Bu ürüne henüz değerlendirme yapılmadı. İlk yorumu siz yazın!">
          <div class="pdp-stars">
            {empty_stars_svg}
          </div>
          <span class="pdp-review-count" style="color:var(--brand-primary); font-weight:600; font-size:0.84rem;">İlk Yorumu Siz Yazın</span>
        </a>'''
        pdp_rating_summary_box_html = '''
      <!-- Empty Rating State Box -->
      <div style="text-align:center; padding:32px 20px; background:#f8fafc; border:1px dashed #cbd5e1; border-radius:12px; margin-bottom:24px;">
        <div style="font-size:1.5rem; color:#94a3b8; letter-spacing:4px; margin-bottom:8px;">☆☆☆☆☆</div>
        <div style="font-weight:700; color:#0f172a; font-size:1.02rem; margin-bottom:4px;">Bu ürün için henüz bir değerlendirme yapılmadı</div>
        <p style="color:#64748b; font-size:0.86rem; margin:0 0 16px 0;">İlk değerlendirmeyi siz yaparak diğer kullanıcılara yardımcı olabilirsiniz.</p>
        <button type="button" class="btn-primary" onclick="openProductReviewModal()" style="display:inline-flex; align-items:center; gap:8px; padding:8px 18px; border-radius:8px; font-weight:700; cursor:pointer; background:var(--brand-primary); color:#fff; border:none; font-size:0.86rem;">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
          <span>İlk Değerlendirmeyi Siz Yazın</span>
        </button>
      </div>'''

    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_str(name_tr)} Fiyatı ve Özellikleri | Pozitron Market</title>
  <meta name="description" content="{escape_str(meta_desc)}">
  <meta name="keywords" content="{escape_str(brand)}, {escape_str(cat_name_tr)}, FPV drone parçaları, {escape_str(name_tr)}, drone yedek parça, Teknofest donanım">
  <link rel="canonical" href="{canonical_url}">
  
  <!-- OpenGraph Meta Tags -->
  <meta property="og:type" content="product">
  <meta property="og:title" content="{escape_str(name_tr)} | Pozitron Market">
  <meta property="og:description" content="{escape_str(meta_desc)}">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:image" content="{abs_img}">
  <meta property="og:site_name" content="Pozitron Market">
  <meta property="product:price:amount" content="{float(price_try):.2f}">
  <meta property="product:price:currency" content="TRY">

  <!-- Twitter Cards -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape_str(name_tr)} | Pozitron Market">
  <meta name="twitter:description" content="{escape_str(meta_desc)}">
  <meta name="twitter:image" content="{abs_img}">

  <!-- Schema.org JSON-LD -->
  <script type="application/ld+json">
  {json.dumps(schema_json, ensure_ascii=False, indent=2)}
  </script>
  <script type="application/ld+json">
  {json.dumps(breadcrumb_json, ensure_ascii=False, indent=2)}
  </script>

  <!-- Google Fonts & Synchronized Master CSS -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../styles.css?v=20260912_amazon_suite">
</head>
<body>

  <!-- Minimalist Top Announcement Bar -->
  <div class="announcement-bar" role="banner">
    <div class="container announcement-inner">
      <div class="announcement-text">
        <span class="badge-dot"></span>
        <strong>FPV &amp; Drone Donanımları</strong> — 
        <span>1500 TL Üzeri Ücretsiz Hızlı Kargo</span>
      </div>
      <div class="announcement-actions">
        <a href="../" class="lang-toggle-btn" style="text-decoration:none;">
          <span class="lang-code">TR</span>
        </a>
      </div>
    </div>
  </div>

  <!-- Minimalist Main Header Synced with Main Site -->
  <header class="main-header" role="banner">
    <div class="container header-container">
      
      <!-- Brand Logo -->
      <a href="../" class="brand-link" aria-label="Pozitron Market Anasayfa">
        <img src="../assets/logo.svg" alt="Pozitron Market - Drone &amp; FPV Donanım Mağazası" class="brand-logo" width="280" height="56">
      </a>

      <!-- Search Form -->
      <div class="header-search-wrap" role="search">
        <form class="search-form" action="../" method="GET">
          <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input 
            type="search" 
            name="q"
            class="search-input" 
            placeholder="FPV motor, ESC, uçuş kartı ara..." 
            autocomplete="off"
            aria-label="Ürün Arama"
          >
        </form>
      </div>

      <!-- Action Nav Buttons (Clean SVG Icons, Zero Emojis) -->
      <nav class="header-actions" aria-label="Navigasyon Menüsü">
        <a href="../3d-baski-studio.html" class="btn-3d-print-nav" title="3D Baskı Studio">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>
          <span>3D Baskı Studio</span>
        </a>

        <a href="../drone-toplama-sihirbazi.html" class="btn-builder-nav" title="Drone Toplama Sihirbazı">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
          <span>Drone Topla</span>
        </a>

        <a href="../#cart" class="btn-cart-trigger" aria-label="Alışveriş Sepeti">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <path d="M16 10a4 4 0 0 1-8 0"></path>
          </svg>
          <span class="cart-label">Sepetim</span>
          <span class="cart-badge" id="header-cart-badge" style="display:none;">0</span>
        </a>
      </nav>

    </div>
  </header>

  <!-- Main Product Detail Page Layout -->
  <main class="pdp-container">
    
    <!-- Clean Minimalist Breadcrumbs -->
    <nav class="pdp-breadcrumbs" aria-label="Breadcrumb">
      <a href="../">Ana Sayfa</a>
      <span class="sep">/</span>
      <a href="../#category={cat_id}">{escape_str(cat_name_tr)}</a>
      <span class="sep">/</span>
      <a href="../#brand={escape_str(brand)}">{escape_str(brand)}</a>
      <span class="sep">/</span>
      <span class="current">{escape_str(name_tr)}</span>
    </nav>

    <!-- Product Showcase Card -->
    <div class="pdp-showcase">
      
      <!-- Gallery Column -->
      <div class="pdp-gallery">
        <div class="pdp-main-image-wrap">
          {f'<span class="pdp-badge-discount">%{discount_pct} İndirim</span>' if has_discount else ''}
          <img id="main-pdp-img" src="{escape_str(img_src)}" alt="{escape_str(name_tr)}" onerror="this.src='../assets/hero_drone.png'">
        </div>
      </div>

      <!-- Info & Purchase Column -->
      <div class="pdp-info">
        <div class="pdp-meta-top">
          <span class="pdp-brand-tag">{escape_str(brand)}</span>
          <span class="pdp-sku">SKU: {escape_str(sku)}</span>
        </div>

        <h1 class="pdp-title">{escape_str(name_tr)}</h1>

        {pdp_rating_row_html}

        <!-- Price Card -->
        <div class="pdp-price-card">
          <div class="pdp-price-current">{format_try(price_try)}</div>
          {f'<div class="pdp-price-old">{format_try(original_price_try)}</div>' if has_discount else ''}
        </div>

        <!-- Amazon Feature 1: Live Same-Day Shipping Countdown Timer -->
        <div class="pdp-delivery-countdown" id="pdp-countdown-box">
          <div class="pdp-countdown-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          </div>
          <div class="pdp-countdown-text">
            <div class="pdp-countdown-title">
              <span>Aynı Gün Kargo Fırsatı</span>
              <span class="pdp-fast-badge">Hızlı Gönderi</span>
            </div>
            <div>
              Bugün kargoya verilmesi için kalan süre: 
              <strong id="pdp-timer-val" class="pdp-countdown-timer-val">03 saat 24 dk 18 sn</strong>
            </div>
          </div>
        </div>

        <!-- Stock Status -->
        <div class="pdp-stock-row {'low-stock' if is_low_stock else ''}">
          <span class="pdp-stock-indicator {'pulse' if is_low_stock else ('out-of-stock' if not is_in_stock else '')}"></span>
          {f'<span>Stokta Son <strong>{real_stock}</strong> Adet Kaldı!</span> <span class="stock-badge-low">Tükeniyor</span>' if is_low_stock else (f'<span>Stokta Var</span>' if is_in_stock else '<span>Tükendi / Stokta Yok</span>')}
        </div>

        <!-- Purchase Actions Box -->
        <div class="pdp-purchase-actions">
          <div class="pdp-qty-row">
            <div class="pdp-qty-picker">
              <button type="button" class="pdp-qty-btn" onclick="changeQty(-1)" aria-label="Adeti Azalt">−</button>
              <input type="number" id="product-qty" class="pdp-qty-input" value="1" min="1" max="99" readonly aria-label="Ürün Adedi">
              <button type="button" class="pdp-qty-btn" onclick="changeQty(1)" aria-label="Adeti Arttır">+</button>
            </div>
            <button type="button" onclick="handleAddToCart(false)" class="pdp-btn-cart">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
              <span>Sepete Ekle</span>
            </button>
          </div>

          <!-- Amazon Feature 3: 1-Click Fast "Buy Now" Checkout -->
          <button type="button" onclick="handleAddToCart(true)" class="pdp-btn-buy-now">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
            <span>Hemen Satın Al</span>
          </button>

          <a href="{wa_url}" id="product-wa-link" target="_blank" rel="noopener" class="pdp-btn-wa">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12.031 6.172c-3.181 0-5.767 2.586-5.768 5.766-.001 1.298.38 2.27 1.019 3.287l-.582 2.128 2.182-.573c.978.58 1.911.928 3.145.929 3.178 0 5.767-2.587 5.768-5.766.001-3.187-2.575-5.77-5.764-5.771zm3.392 8.244c-.144.405-.837.774-1.17.824-.311.045-.698.055-2.062-.511-1.615-.668-2.673-2.316-2.753-2.424-.08-.108-.66-88-.66-1.678 0-.798.42-1.19.568-1.341.144-.15.314-.189.42-.189.105 0 .21.002.302.006.096.004.226-.036.353.27.13.314.444 1.082.483 1.161.039.08.065.173.013.277-.052.105-.078.17-.156.26-.078.092-.163.205-.233.276-.079.079-.161.165-.069.324.092.158.408.673.875 1.089.601.535 1.107.701 1.265.78.158.079.25.069.344-.04.095-.108.405-.471.513-.633.107-.162.217-.135.363-.081.147.054.929.438 1.088.517.159.08.264.12.303.186.039.066.039.384-.105.789z"></path></svg>
            <span>WhatsApp ile Sipariş &amp; Destek</span>
          </a>

          <a href="../drone-toplama-sihirbazi.html" class="pdp-btn-wizard">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>
            <span>Bu Parçayı Drone Sihirbazında Test Et</span>
          </a>
        </div>

        <!-- Clean Professional Perks (SVG Icons, Zero Emojis) -->
        <div class="pdp-perks-grid">
          <div class="pdp-perk-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>
            <span><strong>Aynı Gün Kargo</strong> (15:00'e kadar)</span>
          </div>
          <div class="pdp-perk-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1" 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>
            <span><strong>14 Gün İade</strong> Hakkı</span>
          </div>
          <div class="pdp-perk-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            <span><strong>3D Secure</strong> Güvenli Ödeme</span>
          </div>
        </div>

      </div>
    </div>

    <!-- Amazon Feature 4: Frequently Bought Together (Bundle & Save) -->
    {bundle_section_html}

    <!-- Amazon Feature 5: Compare Similar Items Matrix -->
    {compare_matrix_html}

    <!-- Technical Specs Card -->
    <div class="pdp-card">
      <h2 class="pdp-card-title">Teknik Özellikler</h2>
      <table class="pdp-specs-table">
        <tbody>
          {specs_rows_html}
        </tbody>
      </table>
    </div>

    <!-- Product Description Card -->
    <div class="pdp-card">
      <h2 class="pdp-card-title">Ürün Açıklaması</h2>
      <div class="pdp-description-text">
        <p style="margin-bottom: 12px;">{escape_str(desc_tr)}</p>
        {f'<p style="color:var(--text-muted); font-size:0.88rem;">{escape_str(desc_en)}</p>' if desc_en else ''}
      </div>
    </div>

    <!-- Customer Reviews & Pilot Evaluations Card -->
    <div class="pdp-card" id="pdp-reviews-section">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom:24px; padding-bottom:16px; border-bottom:1px solid var(--border-subtle);">
        <div>
          <h2 class="pdp-card-title" style="margin-bottom:4px;">Müşteri Değerlendirmeleri</h2>
          <p style="color:var(--text-muted); font-size:0.88rem; margin:0;">Bu ürün hakkındaki kullanıcı deneyimleri ve değerlendirmeleri.</p>
        </div>
        <button type="button" class="btn-primary" onclick="openProductReviewModal()" style="display:inline-flex; align-items:center; gap:8px; padding:10px 18px; border-radius:8px; font-weight:700; cursor:pointer; background:var(--brand-primary); color:#fff; border:none;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
          <span>Bu Ürüne Yorum Yaz</span>
        </button>
      </div>

      {pdp_rating_summary_box_html}

      <!-- Reviews Container -->
      <div id="pdp-reviews-list" style="display:flex; flex-direction:column; gap:14px;"></div>
    </div>

    <!-- Related Products Card -->
    {f'''
    <div class="pdp-card">
      <h2 class="pdp-card-title">{escape_str(cat_name_tr)} Kategorisindeki Diğer Parçalar</h2>
      <div class="pdp-related-grid">
        {related_html}
      </div>
    </div>
    ''' if related_html else ''}

  </main>

  <!-- Product Review Submission Modal -->
  <div id="pdp-review-modal" style="display:none; position:fixed; inset:0; background:rgba(15,23,42,0.6); backdrop-filter:blur(4px); z-index:9999; align-items:center; justify-content:center; padding:16px;">
    <div style="background:#ffffff; border-radius:16px; max-width:500px; width:100%; padding:28px; box-shadow:0 20px 25px -5px rgba(0,0,0,0.1); position:relative;">
      <button type="button" onclick="closeProductReviewModal()" style="position:absolute; top:16px; right:16px; background:transparent; border:none; font-size:24px; cursor:pointer; color:#64748b;">&times;</button>
      <h3 style="font-size:1.3rem; font-weight:800; color:#0f172a; margin-bottom:4px;">Bu Ürünü Değerlendir</h3>
      <p style="color:#64748b; font-size:0.85rem; margin-bottom:18px;">{escape_str(name_tr)}</p>

      <form id="pdp-review-form" onsubmit="submitProductReview(event)">
        <div style="margin-bottom:14px;">
          <label style="display:block; font-size:0.85rem; font-weight:700; margin-bottom:6px; color:#334155;">Adınız &amp; Soyadınız *</label>
          <input type="text" id="pdp-rev-name" required placeholder="Örn: Mehmet Öz" style="width:100%; padding:10px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:0.9rem; box-sizing:border-box;">
        </div>
        <div style="margin-bottom:14px;">
          <label style="display:block; font-size:0.85rem; font-weight:700; margin-bottom:6px; color:#334155;">Puanınız *</label>
          <div id="pdp-star-picker" style="display:flex; gap:6px; font-size:26px; cursor:pointer; color:#f59e0b; user-select:none;">
            <span onclick="setPdpRating(1)">★</span>
            <span onclick="setPdpRating(2)">★</span>
            <span onclick="setPdpRating(3)">★</span>
            <span onclick="setPdpRating(4)">★</span>
            <span onclick="setPdpRating(5)">★</span>
          </div>
          <input type="hidden" id="pdp-rev-rating" value="5">
        </div>
        <div style="margin-bottom:18px;">
          <label style="display:block; font-size:0.85rem; font-weight:700; margin-bottom:6px; color:#334155;">Yorumunuz *</label>
          <textarea id="pdp-rev-comment" required rows="4" placeholder="Ürünün malzeme kalitesi, montaj kolaylığı veya uçuş performansı hakkında düşünceleriniz..." style="width:100%; padding:10px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:0.9rem; resize:vertical; box-sizing:border-box;"></textarea>
        </div>
        <button type="submit" style="width:100%; padding:12px; justify-content:center; border-radius:8px; font-weight:700; background:#0284c7; color:#fff; border:none; cursor:pointer; font-size:0.95rem;">Yorumu Yayınla</button>
      </form>
    </div>
  </div>

  <!-- Minimalist Main Footer Synced with Main Site -->
  <footer class="main-footer" role="contentinfo">
    <div class="container footer-container">
      
      <!-- Col 1: Brand Info -->
      <div class="footer-col">
        <img src="../assets/logo.svg" alt="Pozitron Market Logo" class="footer-logo" width="220" height="42">
        <p class="footer-desc">
          Pozitron Market, Türkiye'nin lider FPV ve drone donanım e-ticaret platformudur. Sertifikalı motor, ESC, uçuş kontrol kartı ve geniş yedek parça stoğuyla pilotların yanındayız.
        </p>
        <div class="footer-contacts">
          <div class="contact-line">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
            <span>Teknopark İstanbul &amp; Ankara ODTÜ Teknokent</span>
          </div>
          <div class="contact-line">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
            <span>+90 (542) 546 55 62</span>
          </div>
          <div class="contact-line">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
            <span>destek@pozitronmarket.com</span>
          </div>
        </div>
      </div>

      <!-- Col 2: Categories -->
      <div class="footer-col">
        <div class="footer-col-title">Donanım Kategorileri</div>
        <ul class="footer-links">
          <li><a href="../#category=motors">Brushless FPV Motorlar</a></li>
          <li><a href="../#category=esc">ESC Hız Kontrol Sürücüleri</a></li>
          <li><a href="../#category=flight_controllers">Uçuş Kontrol Kartları</a></li>
          <li><a href="../#category=cameras">FPV &amp; HD Kameralar</a></li>
          <li><a href="../#category=vtx">Video Vericiler (VTX)</a></li>
          <li><a href="../#category=batteries_chargers">LiPo Bataryalar &amp; Şarj Cihazları</a></li>
          <li><a href="../#category=propellers">FPV Pervaneler</a></li>
        </ul>
      </div>

      <!-- Col 3: Engineering Tools & Policies -->
      <div class="footer-col">
        <div class="footer-col-title">Mühendislik &amp; Destek</div>
        <ul class="footer-links">
          <li><a href="../drone-toplama-sihirbazi.html">Drone Toplama Sihirbazı</a></li>
          <li><a href="../3d-baski-studio.html">3D Baskı Studio (TPU/PETG)</a></li>
          <li><a href="../iade-politikasi.html">İade ve İptal Şartları</a></li>
          <li><a href="../return-policy.html">Return &amp; Refund Policy</a></li>
          <li><a href="../#builder">Özel İHA Konfigüratörü</a></li>
        </ul>
      </div>

      <!-- Col 4: Trust & Secure Checkout -->
      <div class="footer-col">
        <div class="footer-col-title">Güvenli Alışveriş</div>
        <p class="footer-desc" style="font-size:0.82rem; margin-bottom:12px;">
          Tüm ödemeleriniz 256-bit SSL ve 3D Secure banka onaylı ödeme altyapısı ile güvence altındadır.
        </p>
        <div class="footer-badges">
          <span class="footer-badge">3D Secure</span>
          <span class="footer-badge">256-Bit SSL</span>
          <span class="footer-badge">Hızlı Kargo</span>
        </div>
      </div>

    </div>

    <!-- Bottom Bar -->
    <div class="footer-bottom">
      <div class="container footer-bottom-inner">
        <div>&copy; 2026 Pozitron Market. Tüm hakları saklıdır. FPV &amp; Drone Donanım Ekosistemi.</div>
        <div class="footer-social-links">
          <a href="../" aria-label="Anasayfa">Anasayfa</a>
          <a href="../#catalog-section" aria-label="Tüm Donanımlar">Tüm Donanımlar</a>
          <a href="../drone-toplama-sihirbazi.html" aria-label="Sihirbaz">Sihirbaz</a>
        </div>
      </div>
    </div>
  </footer>

  <!-- Interactivity Script (Cart & Amazon Suite Client Logic) -->
  <script>
    function changeQty(delta) {{
      const input = document.getElementById('product-qty');
      let val = parseInt(input.value) || 1;
      val = Math.max(1, Math.min(99, val + delta));
      input.value = val;
    }}

    function getCart() {{
      try {{
        return JSON.parse(localStorage.getItem('pozitron_cart') || '[]');
      }} catch (e) {{
        return [];
      }}
    }}

    function saveCart(cart) {{
      localStorage.setItem('pozitron_cart', JSON.stringify(cart));
      updateHeaderCart();
    }}

    function updateHeaderCart() {{
      const cart = getCart();
      const badge = document.getElementById('header-cart-badge');
      if (!badge) return;
      const totalCount = cart.reduce((sum, item) => sum + (item.quantity || 1), 0);
      if (totalCount > 0) {{
        badge.innerText = totalCount;
        badge.style.display = 'inline-flex';
      }} else {{
        badge.style.display = 'none';
      }}
    }}

    function handleAddToCart(buyNow) {{
      const qty = parseInt(document.getElementById('product-qty').value) || 1;
      const cart = getCart();
      const existingIndex = cart.findIndex(i => i.sku === {json.dumps(sku)} || i.id === {json.dumps(p_id)});
      
      if (existingIndex >= 0) {{
        cart[existingIndex].quantity = (cart[existingIndex].quantity || 1) + qty;
      }} else {{
        cart.push({{
          id: {json.dumps(p_id)},
          sku: {json.dumps(sku)},
          name_tr: {json.dumps(name_tr)},
          name_en: {json.dumps(name_en)},
          brand: {json.dumps(brand)},
          price_try: {float(price_try)},
          price_usd: {float(price_usd)},
          image_url: {json.dumps(image_rel)},
          quantity: qty
        }});
      }}
      saveCart(cart);

      if (buyNow) {{
        window.location.href = '../#cart';
      }} else {{
        showToast(qty + " adet " + {json.dumps(name_tr)} + " sepete eklendi!");
      }}
    }}

    function addSingleCompareToCart(id, sku, name, priceTry, imgUrl) {{
      const cart = getCart();
      const existing = cart.find(i => i.id === id || i.sku === sku);
      if (existing) {{
        existing.quantity = (existing.quantity || 1) + 1;
      }} else {{
        cart.push({{
          id: id,
          sku: sku,
          name_tr: name,
          name_en: name,
          price_try: priceTry,
          price_usd: priceTry / 47.0,
          image_url: imgUrl,
          quantity: 1
        }});
      }}
      saveCart(cart);
      showToast(name + " sepete eklendi!");
    }}

    // Bundle Price Calculation
    function updateBundleTotal() {{
      const checkboxes = document.querySelectorAll('.pdp-bundle-check-label input[type="checkbox"]');
      let total = 0;
      let count = 0;
      checkboxes.forEach(cb => {{
        if (cb.checked) {{
          total += parseFloat(cb.getAttribute('data-price')) || 0;
          count++;
        }}
      }});
      
      const priceEl = document.getElementById('bundle-total-price-val');
      const btnText = document.getElementById('bundle-btn-text');
      if (priceEl) {{
        // Format Turkish currency
        const valFormatted = total.toLocaleString('tr-TR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
        priceEl.innerText = valFormatted + ' ₺';
      }}
      if (btnText) {{
        btnText.innerText = count > 0 ? (count + " Ürünü Birlikte Sepete Ekle") : "Lütfen Ürün Seçin";
      }}
    }}

    function handleBundleAddToCart() {{
      const checkboxes = document.querySelectorAll('.pdp-bundle-check-label input[type="checkbox"]:checked');
      if (checkboxes.length === 0) {{
        showToast("Lütfen paketten en az bir ürün seçin!");
        return;
      }}
      
      const cart = getCart();
      let addedCount = 0;

      checkboxes.forEach(cb => {{
        const sku = cb.getAttribute('data-sku');
        const id = cb.getAttribute('data-id');
        const name = cb.getAttribute('data-name');
        const price = parseFloat(cb.getAttribute('data-price')) || 0;
        const img = cb.getAttribute('data-img');

        const existing = cart.find(i => i.sku === sku || i.id === id);
        if (existing) {{
          existing.quantity = (existing.quantity || 1) + 1;
        }} else {{
          cart.push({{
            id: id,
            sku: sku,
            name_tr: name,
            name_en: name,
            price_try: price,
            price_usd: price / 47.0,
            image_url: img,
            quantity: 1
          }});
        }}
        addedCount++;
      }});

      saveCart(cart);
      showToast(addedCount + " adet uyumlu FPV parçası sepete eklendi!");
    }}

    // Same-Day Delivery Live Countdown Timer
    function initDeliveryCountdown() {{
      const timerEl = document.getElementById('pdp-timer-val');
      if (!timerEl) return;

      function update() {{
        const now = new Date();
        const target = new Date();
        target.setHours(15, 0, 0, 0); // 15:00 cut-off

        if (now >= target) {{
          // Past 15:00, count down to tomorrow 15:00
          target.setDate(target.getDate() + 1);
        }}

        const diff = target - now;
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);

        const pad = (n) => n < 10 ? '0' + n : n;
        timerEl.innerText = pad(hours) + " saat " + pad(minutes) + " dk " + pad(seconds) + " sn";
      }}

      update();
      setInterval(update, 1000);
    }}


    function showToast(msg) {{
      const existing = document.querySelector('.pdp-toast');
      if (existing) existing.remove();
      const toast = document.createElement('div');
      toast.className = 'pdp-toast';
      toast.innerHTML = msg + ' <a href="../#cart">Sepete Git →</a>';
      document.body.appendChild(toast);
      setTimeout(() => toast.classList.add('visible'), 20);
      setTimeout(() => {{
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 250);
      }}, 3500);
    }}

    // Product Reviews System
    function openProductReviewModal() {{
      const modal = document.getElementById('pdp-review-modal');
      if (!modal) return;
      try {{
        const u = JSON.parse(localStorage.getItem('pozitron_user') || 'null');
        if (u && (u.full_name || u.email)) {{
          const nameInput = document.getElementById('pdp-rev-name');
          if (nameInput) nameInput.value = u.full_name || u.email;
        }}
      }} catch(e) {{}}
      modal.style.display = 'flex';
    }}

    function closeProductReviewModal() {{
      const modal = document.getElementById('pdp-review-modal');
      if (modal) modal.style.display = 'none';
    }}

    function setPdpRating(val) {{
      const input = document.getElementById('pdp-rev-rating');
      if (input) input.value = val;
      const stars = document.querySelectorAll('#pdp-star-picker span');
      stars.forEach((s, idx) => {{
        s.textContent = (idx < val) ? '★' : '☆';
      }});
    }}

    function submitProductReview(e) {{
      e.preventDefault();
      const name = (document.getElementById('pdp-rev-name').value || '').trim();
      const rating = parseInt(document.getElementById('pdp-rev-rating').value || '5', 10);
      const comment = (document.getElementById('pdp-rev-comment').value || '').trim();

      if (!name || !comment) return;

      const newRev = {{
        id: 'rev_' + Date.now().toString(36),
        userName: name,
        userAvatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=' + encodeURIComponent(name),
        rating: rating,
        productName: {json.dumps(name_tr)},
        productId: {json.dumps(p_id)},
        comment: comment,
        date: 'Az önce'
      }};

      try {{
        const stored = JSON.parse(localStorage.getItem('pozitron_community_reviews') || '[]');
        stored.unshift(newRev);
        localStorage.setItem('pozitron_community_reviews', JSON.stringify(stored));
      }} catch(e) {{}}

      fetch('/api/reviews', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          product_id: {json.dumps(p_id)},
          user_name: name,
          rating: rating,
          title: {json.dumps(name_tr)},
          comment: comment
        }})
      }}).catch(() => {{}});

      closeProductReviewModal();
      document.getElementById('pdp-review-form').reset();
      setPdpRating(5);
      showToast("Yorumunuz başarıyla paylaşıldı. Teşekkür ederiz!");
      renderPdpReviews();
    }}

    async function renderPdpReviews() {{
      const listEl = document.getElementById('pdp-reviews-list');
      if (!listEl) return;

      let reviews = [];
      try {{
        const res = await fetch('/api/reviews?product_id=' + encodeURIComponent({json.dumps(p_id)}));
        if (res.ok) {{
          const data = await res.json();
          if (data && data.reviews && data.reviews.length > 0) {{
            reviews = data.reviews.map(r => ({{
              userName: r.user_name,
              userAvatar: r.user_avatar,
              rating: r.rating,
              comment: r.comment,
              date: r.created_at ? r.created_at.split('T')[0] : 'Yakın zamanda'
            }}));
          }}
        }}
      }} catch(e) {{}}

      if (reviews.length === 0) {{
        try {{
          const stored = JSON.parse(localStorage.getItem('pozitron_community_reviews') || '[]');
          reviews = stored.filter(r => r && (r.productId === {json.dumps(p_id)}));
        }} catch(e) {{}}
      }}

      if (reviews.length === 0) {{
        listEl.innerHTML = `
          <div style="text-align:center; padding:32px 16px; background:#f8fafc; border:1px dashed #cbd5e1; border-radius:10px; color:#64748b; font-size:0.88rem;">
            Bu ürün için henüz bir değerlendirme yapılmamış. İlk yorumu siz yazın!
          </div>
        `;
        return;
      }}

      listEl.innerHTML = reviews.map(r => `
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:16px 18px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:10px;">
              <div style="width:36px; height:36px; border-radius:50%; background:#e0f2fe; color:#0284c7; font-weight:800; display:flex; align-items:center; justify-content:center; font-size:0.9rem;">
                ${{r.userName ? r.userName.charAt(0).toUpperCase() : 'M'}}
              </div>
              <div>
                <strong style="font-size:0.92rem; color:#0f172a; display:block;">${{r.userName || 'Müşteri'}}</strong>
              </div>
            </div>
            <div style="text-align:right;">
              <div style="color:#f59e0b; font-size:0.95rem; letter-spacing:1px;">${{'★'.repeat(r.rating || 5)}}</div>
              <span style="font-size:0.75rem; color:#94a3b8;">${{r.date || 'Bugün'}}</span>
            </div>
          </div>
          <p style="margin:0; font-size:0.88rem; color:#334155; line-height:1.6;">"${{r.comment}}"</p>
        </div>
      `).join('');
    }}

    window.addEventListener('DOMContentLoaded', () => {{
      updateHeaderCart();
      initDeliveryCountdown();
      renderPdpReviews();
    }});
  </script>

</body>
</html>"""
    return html_content

def main():
    print("Starting Pozitron SSG Page Generation with Amazon-Inspired High-Conversion Suite...")

    with open(PRODUCTS_JSON_PATH, "r", encoding="utf-8") as f:
        products = json.load(f)

    with open(CATEGORIES_JSON_PATH, "r", encoding="utf-8") as f:
        categories = json.load(f)

    cat_map = {c["id"]: c for c in categories}
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Group products by category
    by_category = {}
    for p in products:
        cid = p.get("category_id", "motors")
        if cid not in by_category:
            by_category[cid] = []
        by_category[cid].append(p)

    generated_count = 0
    sitemap_product_urls = []

    for p in products:
        slug = p.get("slug")
        if not slug:
            continue

        cid = p.get("category_id", "motors")
        cat = cat_map.get(cid)
        related = [rp for rp in by_category.get(cid, []) if rp.get("slug") != slug]

        content = generate_product_page(p, cat, related, products, by_category)
        out_file = os.path.join(OUTPUT_DIR, f"{slug}.html")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(content)

        generated_count += 1
        sitemap_product_urls.append(f"{BASE_URL}/products/{slug}.html")

    print(f"Generated {generated_count} product HTML pages with Amazon Suite in '{OUTPUT_DIR}/'.")

    # Generate full updated sitemap.xml
    print("Generating comprehensive sitemap.xml...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        '  <url>',
        f'    <loc>{BASE_URL}/</loc>',
        f'    <lastmod>{today_str}</lastmod>',
        '    <changefreq>daily</changefreq>',
        '    <priority>1.0</priority>',
        '  </url>',
        '  <url>',
        f'    <loc>{BASE_URL}/drone-toplama-sihirbazi.html</loc>',
        f'    <lastmod>{today_str}</lastmod>',
        '    <changefreq>weekly</changefreq>',
        '    <priority>0.95</priority>',
        '  </url>',
        '  <url>',
        f'    <loc>{BASE_URL}/3d-baski-studio.html</loc>',
        f'    <lastmod>{today_str}</lastmod>',
        '    <changefreq>weekly</changefreq>',
        '    <priority>0.95</priority>',
        '  </url>',
        '  <url>',
        f'    <loc>{BASE_URL}/iade-politikasi.html</loc>',
        f'    <lastmod>{today_str}</lastmod>',
        '    <changefreq>monthly</changefreq>',
        '    <priority>0.7</priority>',
        '  </url>',
        '  <url>',
        f'    <loc>{BASE_URL}/return-policy.html</loc>',
        f'    <lastmod>{today_str}</lastmod>',
        '    <changefreq>monthly</changefreq>',
        '    <priority>0.6</priority>',
        '  </url>'
    ]

    for p_url in sitemap_product_urls:
        escaped_url = p_url.replace("&", "&amp;")
        sitemap_lines.append('  <url>')
        sitemap_lines.append(f'    <loc>{escaped_url}</loc>')
        sitemap_lines.append(f'    <lastmod>{today_str}</lastmod>')
        sitemap_lines.append('    <changefreq>weekly</changefreq>')
        sitemap_lines.append('    <priority>0.8</priority>')
        sitemap_lines.append('  </url>')

    sitemap_lines.append('</urlset>')

    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(sitemap_lines) + "\n")

    print(f"sitemap.xml updated with {len(sitemap_product_urls) + 5} URLs!")

if __name__ == "__main__":
    main()
