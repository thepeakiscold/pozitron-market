#!/usr/bin/env python3
"""
generate_product_pages.py
Static Site Generator (SSG) for Pozitron Market (https://pozitronmarket.com)
Generates 500 individual SEO-optimized HTML product pages fully styled with
the main website's theme (styles.css), clean minimalist layout, zero emojis,
Schema.org Product markup, responsive header/footer, and updates sitemap.xml.
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

def format_try(amount):
    try:
        val = float(amount)
        # Turkish formatting: 1.234,56
        formatted = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} ₺"
    except (ValueError, TypeError):
        return f"{amount} ₺"

def escape_str(s):
    if not s:
        return ""
    return html.escape(str(s).strip(), quote=True)

def generate_product_page(product, category, related_products):
    p_id = product.get("id", "")
    slug = product.get("slug", "")
    sku = product.get("sku", "")
    name_tr = product.get("name_tr") or product.get("name_en") or "FPV Drone Parçası"
    name_en = product.get("name_en") or product.get("name_tr") or ""
    brand = product.get("brand", "Pozitron")
    price_try = product.get("price_try", 0.0)
    price_usd = float(product.get("price_usd") or 0.0)
    original_price_try = product.get("original_price_try", price_try)
    stock = product.get("stock", 50)
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
    rating = product.get("rating", 4.9)
    review_count = max(product.get("review_count", 14), 1)

    cat_name_tr = category.get("name_tr", "Drone Parçaları") if category else "Drone Parçaları"
    cat_id = category.get("id", "motors") if category else "motors"

    canonical_url = f"{BASE_URL}/products/{slug}.html"

    # Meta description snippet (155-160 chars for optimal Google display)
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

    # WhatsApp order link pre-filled
    wa_msg = f"Merhaba, Pozitron Market web sitenizdeki şu ürünü sipariş etmek istiyorum:\n\nÜrün: {name_tr}\nKod: {sku}\nAdet: 1\nFiyat: {format_try(price_try)}\nLink: {canonical_url}"
    import urllib.parse
    wa_url = f"https://wa.me/905442451118?text={urllib.parse.quote(wa_msg)}"

    # Build specs rows (EXCLUDING "warranty_months" and "origin" as requested)
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
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": str(rating),
            "reviewCount": str(review_count),
            "bestRating": "5",
            "worstRating": "1"
        }
    }

    breadcrumb_json = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Ana Sayfa",
                "item": BASE_URL + "/"
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
                "name": name_tr,
                "item": canonical_url
            }
        ]
    }

    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  
  <!-- Primary SEO Meta Tags -->
  <title>{escape_str(name_tr)} Fiyatı ve Özellikleri | Pozitron Market</title>
  <meta name="title" content="{escape_str(name_tr)} Fiyatı ve Özellikleri | Pozitron Market">
  <meta name="description" content="{escape_str(meta_desc)}">
  <meta name="keywords" content="{escape_str(brand)}, {escape_str(cat_name_tr)}, {escape_str(name_tr)}, fpv drone parçaları, drone motoru, esc, uçuş kontrol kartı, teknofest, pozitron market">
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
  <link rel="canonical" href="{canonical_url}">

  <!-- Open Graph / Facebook / WhatsApp -->
  <meta property="og:type" content="product">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:title" content="{escape_str(name_tr)} | Pozitron Market">
  <meta property="og:description" content="{escape_str(meta_desc)}">
  <meta property="og:image" content="{abs_img}">
  <meta property="og:site_name" content="Pozitron Market">
  <meta property="og:price:amount" content="{float(price_try):.2f}">
  <meta property="og:price:currency" content="TRY">

  <!-- Twitter SEO Cards -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:url" content="{canonical_url}">
  <meta name="twitter:title" content="{escape_str(name_tr)} | Pozitron Market">
  <meta name="twitter:description" content="{escape_str(meta_desc)}">
  <meta name="twitter:image" content="{abs_img}">

  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=AW-18404787021"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-89TWF895QG');
    gtag('config', 'AW-18404787021');
  </script>

  <!-- Structured Data (JSON-LD) for Rich Google Search Results -->
  <script type="application/ld+json">
  {json.dumps(schema_json, ensure_ascii=False, indent=2)}
  </script>
  <script type="application/ld+json">
  {json.dumps(breadcrumb_json, ensure_ascii=False, indent=2)}
  </script>

  <!-- Favicon & Stylesheet Synced with Main Site Theme -->
  <link rel="icon" type="image/svg+xml" href="../assets/favicon.svg?v=20260822_v2">
  <link rel="apple-touch-icon" href="../assets/favicon.png?v=20260822_v2">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../styles.css?v=20260824_pdp_theme">
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

        <!-- Rating Row (Crisp SVG Stars, No Emojis) -->
        <div class="pdp-rating-row">
          <div class="pdp-stars">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          </div>
          <span class="pdp-rating-val">{rating}</span>
          <span class="pdp-review-count">({review_count} Pilot Değerlendirmesi)</span>
        </div>

        <!-- Price Card -->
        <div class="pdp-price-card">
          <div class="pdp-price-current">{format_try(price_try)}</div>
          {f'<div class="pdp-price-old">{format_try(original_price_try)}</div>' if has_discount else ''}
        </div>

        <!-- Stock Status Indicator -->
        <div class="pdp-stock-row">
          <span class="pdp-stock-indicator"></span>
          <span>Stokta Var (Hemen Teslim)</span>
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
            <span><strong>Aynı Gün Kargo</strong> (14:00'e kadar)</span>
          </div>
          <div class="pdp-perk-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>
            <span><strong>14 Gün İade</strong> Hakkı</span>
          </div>
          <div class="pdp-perk-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            <span><strong>3D Secure</strong> Güvenli Ödeme</span>
          </div>
        </div>

      </div>
    </div>

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

  <!-- Minimalist Main Footer Synced with Main Site -->
  <footer class="main-footer" role="contentinfo">
    <div class="container footer-container">
      
      <!-- Col 1: Brand Info -->
      <div class="footer-col">
        <img src="../assets/logo.svg" alt="Pozitron Market Logo" class="footer-logo" width="200" height="38">
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
        <h3 class="footer-heading">Drone Donanımları</h3>
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

      <!-- Col 3: Customer Service & Security -->
      <div class="footer-col">
        <h3 class="footer-heading">Müşteri &amp; Güvenlik</h3>
        <ul class="footer-links">
          <li><a href="../drone-toplama-sihirbazi.html">Drone Toplama Sihirbazı</a></li>
          <li><a href="../3d-baski-studio.html">3D Baskı Studio (Özel İmalat)</a></li>
          <li><a href="../iade-politikasi.html" target="_blank" rel="noopener">İade ve Geri Ödeme Politikası</a></li>
          <li><a href="../return-policy.html" target="_blank" rel="noopener">Return Policy (EN)</a></li>
          <li><a href="https://wa.me/905442451118">WhatsApp Canlı Destek</a></li>
        </ul>
      </div>

      <!-- Col 4: Payment Badges -->
      <div class="footer-col">
        <h3 class="footer-heading">Güvenli Ödeme</h3>
        <p class="footer-text">
          Tüm işlemler 256-Bit SSL sertifikası ve 3D Secure banka güvenlik protokolüyle korunmaktadır.
        </p>
        <div class="payment-badges-row">
          <span class="pay-badge">VISA</span>
          <span class="pay-badge">MasterCard</span>
          <span class="pay-badge">TROY</span>
          <span class="pay-badge">AMEX</span>
          <span class="pay-badge">3D Secure</span>
        </div>
      </div>

    </div>

    <!-- Sub Footer Copyright -->
    <div class="footer-bottom">
      <div class="container footer-bottom-inner">
        <p>© {datetime.now().year} Pozitron Market FPV Hardware Ltd. Tüm hakları saklıdır.</p>
      </div>
    </div>
  </footer>

  <!-- Interactivity Script (Synced with LocalStorage Cart) -->
  <script>
    function getCart() {{
      try {{ return JSON.parse(localStorage.getItem('pozitron_cart') || '[]'); }} catch(e) {{ return []; }}
    }}
    function saveCart(cart) {{
      localStorage.setItem('pozitron_cart', JSON.stringify(cart));
      updateHeaderCart();
    }}
    function updateHeaderCart() {{
      const cart = getCart();
      const count = cart.reduce((acc, it) => acc + (it.quantity || 1), 0);
      const badge = document.getElementById('header-cart-badge');
      if (badge) {{
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-flex' : 'none';
      }}
    }}
    function changeQty(delta) {{
      const inp = document.getElementById('product-qty');
      if (!inp) return;
      let v = parseInt(inp.value, 10) || 1;
      v = Math.max(1, Math.min(99, v + delta));
      inp.value = v;
      updateWaLink(v);
    }}
    function updateWaLink(qty) {{
      const waLink = document.getElementById('product-wa-link');
      if (!waLink) return;
      const baseMsg = "Merhaba, Pozitron Market web sitenizdeki şu ürünü sipariş etmek istiyorum:\\n\\nÜrün: " + {json.dumps(name_tr)} + "\\nKod: " + {json.dumps(sku)} + "\\nAdet: " + qty + "\\nLink: " + {json.dumps(canonical_url)};
      waLink.href = "https://wa.me/905442451118?text=" + encodeURIComponent(baseMsg);
    }}
    function handleAddToCart(buyNow) {{
      const qty = parseInt(document.getElementById('product-qty')?.value, 10) || 1;
      const cart = getCart();
      const existing = cart.find(x => x.id === {json.dumps(p_id)} || x.sku === {json.dumps(sku)});
      if (existing) {{
        existing.quantity += qty;
      }} else {{
        cart.push({{
          id: {json.dumps(p_id)},
          sku: {json.dumps(sku)},
          name_en: {json.dumps(name_en)},
          name_tr: {json.dumps(name_tr)},
          brand: {json.dumps(brand)},
          category_id: {json.dumps(cat_id)},
          price_usd: {price_usd},
          price_try: {float(price_try)},
          image_url: {json.dumps(image_rel)},
          quantity: qty
        }});
      }}
      saveCart(cart);

      // Track GA4 event
      if (typeof gtag === 'function') {{
        gtag('event', 'add_to_cart', {{
          currency: 'TRY',
          value: {float(price_try)} * qty,
          items: [{{
            item_id: {json.dumps(sku)},
            item_name: {json.dumps(name_tr)},
            item_brand: {json.dumps(brand)},
            item_category: {json.dumps(cat_name_tr)},
            price: {float(price_try)},
            quantity: qty
          }}]
        }});
      }}

      if (buyNow) {{
        window.location.href = '../#cart';
      }} else {{
        showToast(qty + " adet " + {json.dumps(name_tr)} + " sepete eklendi!");
      }}
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
    window.addEventListener('DOMContentLoaded', updateHeaderCart);
  </script>

</body>
</html>"""
    return html_content

def main():
    print("Starting Pozitron SSG Page Generation...")

    with open(PRODUCTS_JSON_PATH, "r", encoding="utf-8") as f:
        products = json.load(f)

    with open(CATEGORIES_JSON_PATH, "r", encoding="utf-8") as f:
        categories = json.load(f)

    cat_map = {c["id"]: c for c in categories}

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Group products by category for related recommendations
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

        content = generate_product_page(p, cat, related)
        out_file = os.path.join(OUTPUT_DIR, f"{slug}.html")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(content)

        generated_count += 1
        sitemap_product_urls.append(f"{BASE_URL}/products/{slug}.html")

    print(f"Generated {generated_count} product HTML pages in '{OUTPUT_DIR}/'.")

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
