#!/usr/bin/env python3
"""
generate_product_pages.py
Static Site Generator (SSG) for Pozitron Market (https://pozitronmarket.com)
Generates 500 individual SEO-optimized HTML product pages with full Schema.org Product markup,
OpenGraph tags, responsive layout, direct purchase links, and updates sitemap.xml.
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
    slug = product.get("slug", "")
    sku = product.get("sku", "")
    name_tr = product.get("name_tr") or product.get("name_en") or "FPV Drone Parçası"
    name_en = product.get("name_en") or product.get("name_tr") or ""
    brand = product.get("brand", "Pozitron")
    price_try = product.get("price_try", 0.0)
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
    cat_icon = category.get("icon", "📦") if category else "📦"

    canonical_url = f"{BASE_URL}/products/{slug}.html"

    # Meta description snippet (155-160 chars for optimal Google display)
    clean_desc_tr = re.sub(r'<[^>]+>', '', desc_tr).replace('"', '&quot;').strip()
    meta_desc = f"{name_tr} en uygun fiyatla Pozitron Market'te! {brand} marka orijinal ürün, teknik özellikleri, aynı gün kargo ve taksit fırsatıyla hemen inceleyin."
    if len(meta_desc) > 165:
        meta_desc = meta_desc[:162] + "..."

    # Discount calculation
    has_discount = False
    discount_pct = 0
    if original_price_try and original_price_try > price_try:
        has_discount = True
        discount_pct = int(round(((original_price_try - price_try) / original_price_try) * 100))

    # WhatsApp order link pre-filled
    wa_msg = f"Merhaba, Pozitron Market web sitenizdeki şu ürün hakkında bilgi almak ve sipariş vermek istiyorum:\n\n*Ürün:* {name_tr}\n*Kod:* {sku}\n*Fiyat:* {format_try(price_try)}\n*Link:* {canonical_url}"
    import urllib.parse
    wa_url = f"https://wa.me/905442451118?text={urllib.parse.quote(wa_msg)}"

    # Build specs rows
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
        "warranty_months": "Garanti Süresi",
        "origin": "Orijinallik Durumu",
        "in_the_box": "Kutu İçeriği"
    }

    for key, label in spec_labels.items():
        val = specs.get(key)
        if val:
            display_val = f"{val} g" if key == "weight_g" and not str(val).endswith("g") else f"{val} mm" if key == "dimensions_mm" and not str(val).endswith("mm") else f"{val} Ay Resmi Pozitron Garantisi" if key == "warranty_months" else str(val)
            specs_rows_html += f"""
              <tr>
                <td class="spec-label">{escape_str(label)}</td>
                <td class="spec-value">{escape_str(display_val)}</td>
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
          <a href="./{rel_slug}.html" class="related-card">
            <div class="related-img-wrap">
              <img src="{escape_str(rel_img_src)}" alt="{escape_str(rel_name)}" loading="lazy" onerror="this.src='../assets/hero_drone.png'">
            </div>
            <div class="related-info">
              <div class="related-title">{escape_str(rel_name)}</div>
              <div class="related-price">{format_try(rel_price)}</div>
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

  <link rel="icon" type="image/svg+xml" href="../assets/favicon.svg?v=20260822_v2">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap" rel="stylesheet">

  <style>
    :root {{
      --brand-primary: #0284c7;
      --brand-hover: #0369a1;
      --brand-subtle: #e0f2fe;
      --brand-subtle-text: #0369a1;
      --bg-body: #f8fafc;
      --bg-card: #ffffff;
      --border-color: #e2e8f0;
      --text-primary: #0f172a;
      --text-secondary: #475569;
      --text-muted: #64748b;
      --radius-lg: 16px;
      --radius-md: 10px;
      --radius-sm: 6px;
      --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
      --shadow-md: 0 4px 14px rgba(0,0,0,0.07);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background: var(--bg-body);
      color: var(--text-primary);
      line-height: 1.5;
      padding-bottom: 60px;
    }}

    /* Global Header */
    .site-header {{
      background: #ffffff;
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: var(--shadow-sm);
    }}
    .header-inner {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 12px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    .brand-logo {{
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      color: var(--text-primary);
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-weight: 800;
      font-size: 1.25rem;
      letter-spacing: -0.02em;
    }}
    .brand-logo img {{
      height: 34px;
      width: 34px;
      border-radius: 8px;
    }}
    .header-nav {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .nav-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 14px;
      border-radius: 9999px;
      font-size: 0.88rem;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.2s ease;
    }}
    .nav-pill-wizard {{
      background: #eff6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
    }}
    .nav-pill-wizard:hover {{
      background: #dbeafe;
    }}
    .nav-pill-studio {{
      background: #fdf2f8;
      color: #be185d;
      border: 1px solid #fbcfe8;
    }}
    .nav-pill-studio:hover {{
      background: #fce7f3;
    }}
    .nav-pill-home {{
      background: var(--brand-subtle);
      color: var(--brand-subtle-text);
    }}

    /* Main Container */
    .page-container {{
      max-width: 1240px;
      margin: 24px auto;
      padding: 0 20px;
    }}

    /* Breadcrumbs */
    .breadcrumbs {{
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-bottom: 20px;
    }}
    .breadcrumbs a {{
      color: var(--text-secondary);
      text-decoration: none;
    }}
    .breadcrumbs a:hover {{
      color: var(--brand-primary);
      text-decoration: underline;
    }}
    .breadcrumb-sep {{
      color: #cbd5e1;
    }}

    /* Product Grid */
    .product-layout {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 36px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 32px;
      box-shadow: var(--shadow-sm);
    }}
    @media (max-width: 860px) {{
      .product-layout {{
        grid-template-columns: 1fr;
        padding: 20px;
        gap: 24px;
      }}
    }}

    /* Gallery */
    .gallery-container {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .main-img-box {{
      position: relative;
      background: #f8fafc;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      overflow: hidden;
      aspect-ratio: 1 / 1;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .main-img-box img {{
      max-width: 90%;
      max-height: 90%;
      object-fit: contain;
      transition: transform 0.3s ease;
    }}
    .main-img-box:hover img {{
      transform: scale(1.05);
    }}
    .badge-discount {{
      position: absolute;
      top: 14px;
      left: 14px;
      background: #ef4444;
      color: #ffffff;
      font-size: 0.82rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 9999px;
      box-shadow: 0 2px 6px rgba(239, 68, 68, 0.3);
    }}
    .badge-origin {{
      position: absolute;
      top: 14px;
      right: 14px;
      background: rgba(15, 23, 42, 0.8);
      color: #f8fafc;
      font-size: 0.78rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 6px;
      backdrop-filter: blur(4px);
    }}

    /* Product Details */
    .details-box {{
      display: flex;
      flex-direction: column;
    }}
    .meta-top {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }}
    .brand-tag {{
      background: var(--brand-subtle);
      color: var(--brand-subtle-text);
      font-size: 0.82rem;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .sku-tag {{
      font-size: 0.82rem;
      color: var(--text-muted);
      font-family: monospace;
    }}
    .product-title {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 1.65rem;
      font-weight: 800;
      line-height: 1.3;
      color: var(--text-primary);
      margin-bottom: 12px;
      letter-spacing: -0.02em;
    }}
    .rating-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 18px;
    }}
    .stars {{
      color: #f59e0b;
      font-size: 0.95rem;
    }}
    .rating-score {{
      font-weight: 700;
      font-size: 0.92rem;
    }}
    .review-count {{
      color: var(--text-muted);
      font-size: 0.85rem;
    }}

    /* Price Section */
    .price-box {{
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      border-radius: var(--radius-md);
      padding: 16px 20px;
      margin-bottom: 22px;
      display: flex;
      align-items: baseline;
      gap: 12px;
    }}
    .current-price {{
      font-size: 2rem;
      font-weight: 800;
      color: var(--text-primary);
      font-family: 'Plus Jakarta Sans', sans-serif;
    }}
    .original-price {{
      font-size: 1.15rem;
      color: var(--text-muted);
      text-decoration: line-through;
    }}

    /* Perks */
    .perks-list {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 24px;
    }}
    .perk-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.85rem;
      color: var(--text-secondary);
      font-weight: 500;
    }}

    /* Action Buttons */
    .actions-box {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 24px;
    }}
    .btn {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 14px 24px;
      border-radius: var(--radius-md);
      font-size: 1rem;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
      border: none;
      transition: all 0.2s ease;
    }}
    .btn-buy {{
      background: var(--brand-primary);
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
    }}
    .btn-buy:hover {{
      background: var(--brand-hover);
      transform: translateY(-1px);
    }}
    .btn-wizard {{
      background: #eff6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
    }}
    .btn-wizard:hover {{
      background: #dbeafe;
    }}
    .btn-wa {{
      background: #25d366;
      color: #ffffff;
    }}
    .btn-wa:hover {{
      background: #20ba5a;
    }}

    /* Specs & Tabs */
    .section-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 28px;
      margin-top: 24px;
      box-shadow: var(--shadow-sm);
    }}
    .section-title {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 1.25rem;
      font-weight: 800;
      margin-bottom: 16px;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .specs-table {{
      width: 100%;
      border-collapse: collapse;
    }}
    .specs-table tr {{
      border-bottom: 1px solid #f1f5f9;
    }}
    .specs-table tr:last-child {{
      border-bottom: none;
    }}
    .spec-label {{
      width: 32%;
      padding: 12px 14px;
      font-weight: 600;
      font-size: 0.88rem;
      color: var(--text-secondary);
      background: #f8fafc;
      border-radius: 4px;
    }}
    .spec-value {{
      padding: 12px 16px;
      font-size: 0.9rem;
      color: var(--text-primary);
    }}

    /* Description */
    .description-text {{
      font-size: 0.95rem;
      line-height: 1.7;
      color: var(--text-secondary);
    }}

    /* Related Products */
    .related-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 16px;
      margin-top: 14px;
    }}
    .related-card {{
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 12px;
      text-decoration: none;
      color: inherit;
      transition: all 0.2s ease;
      display: flex;
      flex-direction: column;
    }}
    .related-card:hover {{
      border-color: var(--brand-primary);
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }}
    .related-img-wrap {{
      aspect-ratio: 1/1;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f8fafc;
      border-radius: var(--radius-sm);
      margin-bottom: 10px;
      overflow: hidden;
    }}
    .related-img-wrap img {{
      max-width: 85%;
      max-height: 85%;
      object-fit: contain;
    }}
    .related-title {{
      font-size: 0.85rem;
      font-weight: 600;
      line-height: 1.35;
      color: var(--text-primary);
      margin-bottom: 6px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    .related-price {{
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--brand-primary);
      margin-top: auto;
    }}

    /* Footer */
    .site-footer {{
      margin-top: 50px;
      border-top: 1px solid var(--border-color);
      background: #ffffff;
      padding: 30px 20px;
      text-align: center;
      font-size: 0.88rem;
      color: var(--text-muted);
    }}
    .footer-links {{
      display: flex;
      justify-content: center;
      gap: 20px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}
    .footer-links a {{
      color: var(--text-secondary);
      text-decoration: none;
    }}
    .footer-links a:hover {{
      color: var(--brand-primary);
    }}
  </style>
</head>
<body>

  <!-- Header -->
  <header class="site-header">
    <div class="header-inner">
      <a href="../" class="brand-logo">
        <img src="../assets/hero_drone.png" alt="Pozitron Market Logo">
        <span>Pozitron Market</span>
      </a>
      <nav class="header-nav">
        <a href="../drone-toplama-sihirbazi.html" class="nav-pill nav-pill-wizard">
          ⚡ <span>Drone Toplama Sihirbazı</span>
        </a>
        <a href="../3d-baski-studio.html" class="nav-pill nav-pill-studio">
          🖨️ <span>3D Baskı Studio</span>
        </a>
        <a href="../#category={cat_id}" class="nav-pill nav-pill-home">
          {escape_str(cat_icon)} <span>{escape_str(cat_name_tr)}</span>
        </a>
      </nav>
    </div>
  </header>

  <main class="page-container">
    <!-- Breadcrumbs -->
    <nav class="breadcrumbs" aria-label="Breadcrumb">
      <a href="../">Ana Sayfa</a>
      <span class="breadcrumb-sep">/</span>
      <a href="../#category={cat_id}">{escape_str(cat_name_tr)}</a>
      <span class="breadcrumb-sep">/</span>
      <a href="../#brand={escape_str(brand)}">{escape_str(brand)}</a>
      <span class="breadcrumb-sep">/</span>
      <span>{escape_str(name_tr)}</span>
    </nav>

    <!-- Product Layout -->
    <div class="product-layout">
      <!-- Gallery Column -->
      <div class="gallery-container">
        <div class="main-img-box">
          {f'<span class="badge-discount">%{discount_pct} İndirim</span>' if has_discount else ''}
          <span class="badge-origin">Orijinal Donanım</span>
          <img src="{escape_str(img_src)}" alt="{escape_str(name_tr)}" onerror="this.src='../assets/hero_drone.png'">
        </div>
      </div>

      <!-- Details Column -->
      <div class="details-box">
        <div class="meta-top">
          <span class="brand-tag">{escape_str(brand)}</span>
          <span class="sku-tag">SKU: {escape_str(sku)}</span>
        </div>

        <h1 class="product-title">{escape_str(name_tr)}</h1>

        <div class="rating-row">
          <span class="stars">★★★★★</span>
          <span class="rating-score">{rating}</span>
          <span class="review-count">({review_count} Doğrulanmış Pilot Değerlendirmesi)</span>
        </div>

        <div class="price-box">
          <div class="current-price">{format_try(price_try)}</div>
          {f'<div class="original-price">{format_try(original_price_try)}</div>' if has_discount else ''}
        </div>

        <div class="perks-list">
          <div class="perk-item">✅ <strong>Aynı Gün Kargo</strong> (14:00'e kadar)</div>
          <div class="perk-item">🛡️ <strong>12 Ay Pozitron Garantisi</strong></div>
          <div class="perk-item">🔄 <strong>14 Gün Koşulsuz İade</strong></div>
          <div class="perk-item">💳 <strong>Havale & Güvenli Ödeme</strong></div>
        </div>

        <div class="actions-box">
          <a href="../#product={escape_str(slug)}" class="btn btn-buy">
            🛒 Sepete Ekle & Hemen Satın Al
          </a>
          <a href="../drone-toplama-sihirbazi.html" class="btn btn-wizard">
            ⚡ Bu Parçayı Drone Sihirbazında Test Et
          </a>
          <a href="{wa_url}" target="_blank" rel="noopener" class="btn btn-wa">
            💬 WhatsApp ile Hızlı Sipariş / Destek
          </a>
        </div>
      </div>
    </div>

    <!-- Technical Specs -->
    <div class="section-card">
      <h2 class="section-title">📐 Teknik Özellikler & Veri Tablosu</h2>
      <table class="specs-table">
        <tbody>
          {specs_rows_html}
        </tbody>
      </table>
    </div>

    <!-- Description -->
    <div class="section-card">
      <h2 class="section-title">📝 Ürün Açıklaması & Detaylar</h2>
      <div class="description-text">
        <p style="margin-bottom: 12px;">{escape_str(desc_tr)}</p>
        {f'<p style="color:var(--text-muted); font-size:0.88rem;">{escape_str(desc_en)}</p>' if desc_en else ''}
      </div>
    </div>

    <!-- Related Products -->
    {f'''
    <div class="section-card">
      <h2 class="section-title">🔗 {escape_str(cat_name_tr)} Kategorisindeki Diğer Parçalar</h2>
      <div class="related-grid">
        {related_html}
      </div>
    </div>
    ''' if related_html else ''}
  </main>

  <!-- Footer -->
  <footer class="site-footer">
    <div class="footer-links">
      <a href="../">Ana Sayfa</a>
      <a href="../drone-toplama-sihirbazi.html">Drone Toplama Sihirbazı</a>
      <a href="../3d-baski-studio.html">3D Baskı Studio</a>
      <a href="../iade-politikasi.html">İade ve Teslimat Politikası</a>
      <a href="../return-policy.html">Return Policy</a>
      <a href="https://wa.me/905442451118">WhatsApp İletişim (+90 544 245 11 18)</a>
    </div>
    <p>© {datetime.now().year} Pozitron Market - Türkiye'nin En Kapsamlı FPV Drone Donanım Pazarı.</p>
  </footer>

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

    print(f"✅ Generated {generated_count} product HTML pages in '{OUTPUT_DIR}/'.")

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

    print(f"✅ sitemap.xml updated with {len(sitemap_product_urls) + 5} URLs!")

if __name__ == "__main__":
    main()
