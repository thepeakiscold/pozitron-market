"""
Duplicate Guard — otonom tekrar (duplicate) tespit ve onarim motoru.

Iki kanali denetler:
  1. Instagram gonderileri: tekrar eden basliklar, yakin-kopya metinler ve
     gorsel olarak neredeyse ayni olan fotograflar (perceptual hash).
  2. Site rehberleri (SEO makaleleri): tekrar eden baslik/odak, sayac eki ile
     uretilmis kopya rehberler ve yakin-kopya icerik.

Tespit edilen tekrarlari QA Sentinel saglik denetimine raporlar ve evrim
dongusunde onarim (remediation) aksiyonu alir.
"""
import os
import re
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'pozitron.db')

# Sayac ekli kopya basliklari yakalamak icin: "Baslik (9265)" veya "Baslik #12"
_COUNTER_SUFFIX_RE = re.compile(r'\s*(?:\(|\[)?#?\d{2,6}(?:\)|\])?\s*$')
_NONWORD_RE = re.compile(r'[^a-z0-9çğıöşü ]+')

# Facet phrases used by the old combinatorial guide generator; used to collapse
# near-duplicate "same subject, different facet" article titles.
FACET_MARKERS = [
    'kurulum ve kalibrasyon', 'hata giderme', 'performans optimizasyonu',
    'seçim kriterleri', 'secim kriterleri', 'ölçüm ve test yöntemleri',
    'olcum ve test yontemleri', 'termal yönetim', 'termal yonetim',
    'güvenlik ve koruma', 'guvenlik ve koruma', 'bakım prosedürleri',
    'bakim prosedurleri', 'karşılaştırmalı analiz', 'karsilastirmali analiz',
    'ileri seviye ince ayar',
]


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_text(text: str) -> str:
    """Kucuk harfe cevirip bosluk/noktalama temizler."""
    if not text:
        return ''
    text = str(text).lower().strip()
    text = _NONWORD_RE.sub(' ', text)
    return ' '.join(text.split())


def strip_counter(text: str) -> str:
    """Baslik sonundaki sayaç ekini temizler: '... Sistemleri 9265' -> '... sistemleri'."""
    if not text:
        return ''
    cleaned = _COUNTER_SUFFIX_RE.sub('', str(text).strip())
    return cleaned.strip()


def title_signature(text: str) -> str:
    """Sayaç eki temizlenmis normalize baslik imzasi."""
    return normalize_text(strip_counter(text))


def caption_signature(caption: str, n: int = 60) -> str:
    if not caption:
        return ''
    text = re.sub(r'\s+', ' ', str(caption)).strip().lower()
    text = _NONWORD_RE.sub('', text)
    return text[:n]


def _text_signature(text: str, words: int = 100) -> str:
    if not text:
        return ''
    return ' '.join(str(text).split()[:words]).strip().lower()


def _seo_clone_key(title: str) -> str:
    """
    Collapses facet-variant clone titles to a common key, e.g.
    "Betaflight 4.5 Uçuş Kontrolcüsü kurulum ve kalibrasyon: Kapsamlı ... Rehberi"
    and "Betaflight 4.5 Uçuş Kontrolcüsü: Performans Optimizasyonu Rehberi"
    both map to "betaflight 4 5 uçuş kontrolcüsü".
    """
    t = (title or "").lower()
    t = _COUNTER_SUFFIX_RE.sub('', t)
    for marker in FACET_MARKERS:
        t = t.replace(marker, ' ')
    t = _NONWORD_RE.sub(' ', t)
    drop = {'kapsamli', 'kapsamlı', 'muhendislik', 'mühendislik', 've', 'donanim', 'donanım',
            'rehberi', 'rehber', 'ileri', 'seviye', 'ince', 'ayar', 'kapsamli'}
    words = [w for w in t.split() if w not in drop]
    return ' '.join(words)


class DuplicateGuard:
    def __init__(self):
        self.instagram_report = {}
        self.seo_report = {}

    # ------------------------------------------------------------------
    # Instagram
    # ------------------------------------------------------------------
    def scan_instagram(self, limit: int = 2000) -> dict:
        """Tekrar eden baslik, metin (caption) ve gorselleri bulur."""
        try:
            from instagram_agent.db import get_instagram_posts
            posts = get_instagram_posts(limit=limit)
        except Exception as e:
            return {"error": str(e), "status": "UNKNOWN", "duplicate_groups": 0}

        title_groups = {}
        caption_groups = {}
        for p in posts:
            tsig = title_signature(p.get('title', ''))
            if tsig:
                title_groups.setdefault(tsig, []).append(p)
            csig = caption_signature(p.get('caption', ''))
            if csig:
                caption_groups.setdefault(csig, []).append(p)

        dup_titles = {k: v for k, v in title_groups.items() if len(v) > 1}
        dup_captions = {k: v for k, v in caption_groups.items() if len(v) > 1}

        # Gorsel tekrarlari (perceptual hash)
        image_dupes = self._scan_instagram_images(posts)

        all_groups = []
        for sig, group in dup_titles.items():
            all_groups.append({
                "kind": "title", "signature": sig,
                "count": len(group),
                "post_ids": [g["id"] for g in group],
                "titles": [g.get("title", "")[:70] for g in group[:3]],
            })
        for sig, group in dup_captions.items():
            all_groups.append({
                "kind": "caption", "signature": sig[:40],
                "count": len(group),
                "post_ids": [g["id"] for g in group],
            })
        all_groups.extend(image_dupes)

        self.instagram_report = {
            "status": "DEGRADED" if all_groups else "HEALTHY",
            "total_posts_scanned": len(posts),
            "duplicate_groups": len(all_groups),
            "duplicate_title_groups": len(dup_titles),
            "duplicate_caption_groups": len(dup_captions),
            "duplicate_image_groups": len(image_dupes),
            "redundant_posts": sum(g["count"] - 1 for g in all_groups),
            "groups": all_groups[:50],
        }
        # Remediation needs the full, uncapped group list.
        self._ig_all_groups = all_groups
        return self.instagram_report

    def _scan_instagram_images(self, posts: list, threshold: int = 5) -> list:
        try:
            from instagram_agent.image_generator import perceptual_hash, hamming_distance
        except Exception:
            return []

        hashed = []
        for p in posts:
            h = (p.get('metadata') or {}).get('image_hash')
            if not h:
                rel = p.get('local_image_path') or p.get('image_url') or ''
                abs_p = os.path.join(BASE_DIR, rel.lstrip('./').lstrip('/'))
                if rel.lower().endswith(('.jpg', '.jpeg', '.png')) and os.path.exists(abs_p):
                    h = perceptual_hash(abs_p)
            if h:
                hashed.append((p, h))

        groups = []
        used = set()
        for i in range(len(hashed)):
            if i in used:
                continue
            cluster = [hashed[i]]
            for j in range(i + 1, len(hashed)):
                if j in used:
                    continue
                if hamming_distance(hashed[i][1], hashed[j][1]) <= threshold:
                    cluster.append(hashed[j])
                    used.add(j)
            if len(cluster) > 1:
                used.add(i)
                groups.append({
                    "kind": "image",
                    "signature": "phash",
                    "count": len(cluster),
                    "post_ids": [c[0]["id"] for c in cluster],
                })
        return groups

    def remediate_instagram(self, keep: str = "newest", max_delete: int = 200) -> dict:
        """
        Tekrar gruplarindan her birinde bir gonderiyi tutar, gerçek kopyalari kaldirir.
        Baslik ve gorsel tekrarlari otomatik silinir; yalnizca metin (caption) tekrari
        olan gonderiler silinmez, 'flagged' olarak raporlanir (yanlis silmeyi onlemek icin).
        Varsayilan olarak en yeni gonderi tutulur.
        """
        if not self.instagram_report:
            self.scan_instagram()
        try:
            from instagram_agent.db import get_instagram_posts, delete_instagram_post
        except Exception as e:
            return {"error": str(e), "deleted": 0}

        id_to_post = {p["id"]: p for p in get_instagram_posts(limit=2000)}
        groups = getattr(self, "_ig_all_groups", None) or self.instagram_report.get("groups", [])
        to_delete = set()
        flagged = 0
        for grp in groups:
            ids = [pid for pid in grp.get("post_ids", []) if pid in id_to_post]
            if len(ids) <= 1:
                continue
            if grp.get("kind") == "caption":
                # Yalnizca metin benzerligi -> silme, isaretle.
                flagged += len(ids) - 1
                continue
            ids_sorted = sorted(ids, key=lambda i: (id_to_post[i].get("created_at") or ""), reverse=(keep == "newest"))
            for pid in ids_sorted[1:]:
                to_delete.add(pid)

        deleted = 0
        if to_delete:
            to_delete_list = list(to_delete)[:max_delete]
            try:
                from instagram_agent.db import get_db as _ig_db, sync_posts_to_json
                conn = _ig_db()
                cur = conn.cursor()
                for pid in to_delete_list:
                    post = id_to_post.get(pid) or {}
                    rel = post.get('local_image_path') or ''
                    if rel:
                        abs_p = os.path.join(BASE_DIR, rel.lstrip('./').lstrip('/'))
                        try:
                            if os.path.exists(abs_p):
                                os.remove(abs_p)
                        except Exception:
                            pass
                    cur.execute("DELETE FROM instagram_posts WHERE id = ?", (pid,))
                conn.commit()
                conn.close()
                deleted = len(to_delete_list)
                sync_posts_to_json()
            except Exception:
                # Fallback to per-item delete
                try:
                    from instagram_agent.db import delete_instagram_post
                    deleted = sum(1 for pid in to_delete_list if delete_instagram_post(pid))
                except Exception:
                    deleted = 0

        return {
            "deleted": deleted,
            "flagged_caption_duplicates": flagged,
            "kept": len(id_to_post) - deleted,
            "status": "HEALED" if deleted else "NOOP",
        }

    # ------------------------------------------------------------------
    # Site rehberleri (SEO makaleleri)
    # ------------------------------------------------------------------
    def scan_seo(self) -> dict:
        """Tekrar eden rehber baslik/odak ve yakin-kopya icerikleri bulur."""
        conn = _get_db()
        try:
            rows = conn.execute(
                "SELECT id, slug, title, component_focus, content_markdown, created_at "
                "FROM seo_articles ORDER BY id ASC"
            ).fetchall()
        except Exception as e:
            conn.close()
            return {"error": str(e), "status": "UNKNOWN", "duplicate_groups": 0}
        conn.close()

        title_groups = {}
        content_groups = {}
        counter_titles = []
        for r in rows:
            tsig = title_signature(r["title"] or "")
            if tsig:
                title_groups.setdefault(tsig, []).append(dict(r))
            content_sig = _text_signature(r["content_markdown"] or "", 100)
            if content_sig:
                content_groups.setdefault(content_sig, []).append(dict(r))
            if _COUNTER_SUFFIX_RE.search((r["title"] or "").strip()) or _COUNTER_SUFFIX_RE.search((r["component_focus"] or "").strip()):
                counter_titles.append(dict(r))

        dup_titles = {k: v for k, v in title_groups.items() if len(v) > 1}
        dup_content = {k: v for k, v in content_groups.items() if len(v) > 1}

        groups = []
        for sig, group in dup_titles.items():
            groups.append({
                "kind": "seo_title", "signature": sig[:70],
                "count": len(group),
                "slugs": [g["slug"] for g in group[:5]],
                "title": group[0]["title"][:80],
            })
        for sig, group in dup_content.items():
            groups.append({
                "kind": "seo_content", "signature": sig[:50],
                "count": len(group),
                "slugs": [g["slug"] for g in group[:5]],
            })
        if counter_titles:
            groups.append({
                "kind": "seo_counter_clone",
                "signature": "counter-suffix titles",
                "count": len(counter_titles),
                "slugs": [g["slug"] for g in counter_titles[:5]],
            })

        self.seo_report = {
            "status": "DEGRADED" if groups else "HEALTHY",
            "total_articles": len(rows),
            "duplicate_groups": len(groups),
            "duplicate_title_groups": len(dup_titles),
            "duplicate_content_groups": len(dup_content),
            "counter_clone_count": len(counter_titles),
            "redundant_articles": sum(g["count"] - 1 for g in groups if g["kind"] != "seo_counter_clone") + len(counter_titles),
            "groups": groups[:50],
        }
        return self.seo_report

    def remediate_seo(self) -> dict:
        """SEO ajaninin temizleme rutinini calistirir ve statik disa aktarimi senkronlar."""
        try:
            from orchestrator.subagent_seo import TechnicalSeoAgent
            agent = TechnicalSeoAgent()
            res = agent.deduplicate_existing_articles()
            # Ek: sayac ekli kopyalari da temizle
            extra = self._purge_counter_clones()
            res["counter_clones_removed"] = extra
            res["status"] = "HEALED"
            return res
        except Exception as e:
            return {"error": str(e), "status": "FAILED"}

    def _purge_counter_clones(self) -> int:
        """Sayac ekli (NNNN) kopya rehberleri, temel basligin ilk ornegi tutularak siler."""
        conn = _get_db()
        rows = conn.execute("SELECT id, title, component_focus FROM seo_articles ORDER BY id ASC").fetchall()
        seen = set()
        to_delete = []
        to_rename = []
        for r in rows:
            raw_title = (r["title"] or "").strip()
            raw_focus = (r["component_focus"] or "").strip()
            base = title_signature(raw_title) or normalize_text(raw_focus)
            if not base:
                continue
            has_counter = bool(_COUNTER_SUFFIX_RE.search(raw_title) or _COUNTER_SUFFIX_RE.search(raw_focus))
            if base in seen:
                to_delete.append(r["id"])
            else:
                seen.add(base)
                if has_counter:
                    to_rename.append((r["id"], strip_counter(raw_title), strip_counter(raw_focus)))
        if to_delete:
            conn.execute(f"DELETE FROM seo_articles WHERE id IN ({','.join(map(str, to_delete))})")
        for rid, new_title, new_focus in to_rename:
            conn.execute("UPDATE seo_articles SET title = ?, component_focus = ? WHERE id = ?", (new_title, new_focus, rid))
        conn.commit()
        conn.close()
        try:
            from export_data import export_static_data
            export_static_data()
        except Exception:
            pass
        return len(to_delete)

    def plan_seo_clone_cleanup(self):
        """
        Returns a plan of duplicate guides: numbered counter clones and
        same-subject facet variants. Does not modify the database.
        """
        rows = _get_db().execute(
            "SELECT id, slug, title, component_focus FROM seo_articles ORDER BY id ASC"
        ).fetchall()
        # 1. Numbered counter clones: group by stripped base
        base_seen = {}
        delete_ids = []
        rename_map = {}
        for r in rows:
            raw_title = (r["title"] or "").strip()
            raw_focus = (r["component_focus"] or "").strip()
            base = title_signature(raw_title) or normalize_text(raw_focus)
            if not base:
                continue
            if base in base_seen:
                delete_ids.append(r["id"])
            else:
                base_seen[base] = r["id"]
                if _COUNTER_SUFFIX_RE.search(raw_title) or _COUNTER_SUFFIX_RE.search(raw_focus):
                    rename_map[r["id"]] = (strip_counter(raw_title), strip_counter(raw_focus))

        # 2. Facet-variant clones (same subject, different facet)
        key_seen = {}
        for r in rows:
            if r["id"] in delete_ids:
                continue
            title = (r["title"] or "").strip()
            key = _seo_clone_key(title)
            if len(key) < 12:
                continue
            if key in key_seen:
                keep_id = key_seen[key]
                # Prefer the cleaner title (shorter, no "Kapsamlı ..." filler)
                keep_row = next((x for x in rows if x["id"] == keep_id), None)
                keep_title = (keep_row["title"] if keep_row else "") or ""
                if ("Kapsamlı" in keep_title or "Mühendislik" in keep_title) and "Kapsamlı" not in title:
                    delete_ids.append(keep_id)
                    key_seen[key] = r["id"]
                else:
                    delete_ids.append(r["id"])
            else:
                key_seen[key] = r["id"]

        return {"delete_ids": sorted(set(delete_ids)), "rename_map": rename_map, "total": len(rows)}

    def purge_seo_clones(self) -> dict:
        """Removes numbered clones + facet-variant clones from seo_articles and re-exports."""
        plan = self.plan_seo_clone_cleanup()
        delete_ids = plan["delete_ids"]
        conn = _get_db()
        if delete_ids:
            conn.execute(f"DELETE FROM seo_articles WHERE id IN ({','.join(map(str, delete_ids))})")
        for rid, (t, f) in plan["rename_map"].items():
            if rid not in delete_ids:
                conn.execute("UPDATE seo_articles SET title = ?, component_focus = ? WHERE id = ?", (t, f, rid))
        conn.commit()
        remaining = conn.execute("SELECT count(*) FROM seo_articles").fetchone()[0]
        conn.close()
        try:
            from export_data import export_static_data
            export_static_data()
        except Exception:
            pass
        return {
            "deleted": len(delete_ids),
            "renamed": len([r for r in plan["rename_map"] if r not in delete_ids]),
            "remaining": remaining,
            "status": "HEALED",
        }

    # ------------------------------------------------------------------
    # Aggregate
    # ------------------------------------------------------------------
    def scan_all(self) -> dict:
        ig = self.scan_instagram()
        seo = self.scan_seo()
        total_groups = ig.get("duplicate_groups", 0) + seo.get("duplicate_groups", 0)
        return {
            "status": "DEGRADED" if total_groups else "HEALTHY",
            "total_duplicate_groups": total_groups,
            "instagram": ig,
            "seo": seo,
        }

    def remediate_all(self) -> dict:
        ig = self.remediate_instagram()
        seo = self.remediate_seo()
        return {"instagram": ig, "seo": seo, "timestamp": datetime.now().isoformat()}


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--fix', action='store_true', help="Tekrarlari tespit et ve onar")
    args = ap.parse_args()
    guard = DuplicateGuard()
    report = guard.scan_all()
    print(json.dumps(report, ensure_ascii=False, indent=2)[:4000])
    if args.fix:
        print("\n=== ONARIM ===")
        print(json.dumps(guard.remediate_all(), ensure_ascii=False, indent=2))
