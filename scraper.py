"""
Saudi Deals Daily — Scraper
============================
يجلب بيانات المتاجر ويحدّث sites.json في المجلد الرئيسي للمشروع.
التشغيل: python scraper.py
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ══════════════════════════════════════════════════════════════════
# الإعداد
# ══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── مسار sites.json: دائماً في نفس مجلد scraper.py ─────────────
BASE_DIR   = Path(__file__).resolve().parent
SITES_FILE = BASE_DIR / "sites.json"

TIMEOUT     = 12
DELAY       = 1.2
MAX_RETRIES = 2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ══════════════════════════════════════════════════════════════════
# قائمة المتاجر
# ══════════════════════════════════════════════════════════════════

SITES = [
    # متعدد
    {"name": "أمازون السعودية",  "url": "https://www.amazon.sa/deals",                    "cat": "متعدد",      "emoji": "📦", "bg": "#1a1200", "org": "عالمي",  "desc": "أكبر متجر إلكتروني بعروض يومية حصرية وشحن سريع"},
    {"name": "نون السعودية",      "url": "https://www.noon.com/saudi-ar/sale/",             "cat": "متعدد",      "emoji": "🌙", "bg": "#2a2000", "org": "خليجي",  "desc": "المنصة الخليجية الأولى بعروض تصل حتى 70%", "coupon": "NOON15"},
    {"name": "جوميا السعودية",    "url": "https://www.jumia.com.sa/deals/",                "cat": "متعدد",      "emoji": "🛍️", "bg": "#2a1000", "org": "عالمي",  "desc": "عروض يومية متنوعة على آلاف المنتجات"},
    {"name": "تيمو",              "url": "https://www.temu.com/sa",                        "cat": "متعدد",      "emoji": "🛒", "bg": "#2a0018", "org": "عالمي",  "desc": "منتجات متنوعة بأسعار مدهومة مع توصيل للسعودية"},
    # أزياء
    {"name": "نمشي",              "url": "https://sa.namshi.com/sale/",                    "cat": "أزياء",      "emoji": "👗", "bg": "#1a001a", "org": "خليجي",  "desc": "أزياء وأحذية راقية بخصومات كبيرة"},
    {"name": "شي إن",             "url": "https://sa.shein.com/sale-women-sc-00289729.html","cat": "أزياء",      "emoji": "👒", "bg": "#2a001a", "org": "عالمي",  "desc": "أزياء عصرية بأسعار منخفضة جداً", "coupon": "SHEIN20"},
    {"name": "H&M السعودية",      "url": "https://www2.hm.com/ar_sa/sale.html",            "cat": "أزياء",      "emoji": "🏷️", "bg": "#1a000a", "org": "عالمي",  "desc": "أزياء H&M العصرية بتخفيضات موسمية كبيرة"},
    {"name": "زارا السعودية",     "url": "https://www.zara.com/sa/ar/sale-l1299.html",     "cat": "أزياء",      "emoji": "✂️", "bg": "#0a0a0a", "org": "عالمي",  "desc": "مجموعة تصفية زارا بخصومات حصرية"},
    # إلكترونيات
    {"name": "إكسترا",            "url": "https://www.extra.com.sa/ar/offers",             "cat": "إلكترونيات", "emoji": "🖥️", "bg": "#2a0010", "org": "سعودي",  "desc": "أكبر متجر إلكترونيات سعودي بعروض مستمرة"},
    {"name": "إكس سايت",          "url": "https://www.xcite.com/sa-ar/deals",              "cat": "إلكترونيات", "emoji": "📱", "bg": "#001a2a", "org": "خليجي",  "desc": "إلكترونيات وأجهزة بأفضل أسعار الخليج"},
    {"name": "سامسونج السعودية",  "url": "https://www.samsung.com/sa_ar/offer/",           "cat": "إلكترونيات", "emoji": "📺", "bg": "#001525", "org": "عالمي",  "desc": "هواتف وأجهزة سامسونج بأفضل العروض الموسمية"},
    {"name": "أبل السعودية",      "url": "https://www.apple.com/sa-ar/shop/buy-iphone",   "cat": "إلكترونيات", "emoji": "🍎", "bg": "#1a1a1a", "org": "عالمي",  "desc": "أجهزة آبل الأصلية مع برامج تقسيط وضمان معتمد"},
    # جمال
    {"name": "سيفورا",            "url": "https://www.sephora.com/sa/ar/sale",             "cat": "جمال",       "emoji": "🌸", "bg": "#1a0010", "org": "عالمي",  "desc": "أشهر متجر تجميل عالمي بعروض حصرية"},
    {"name": "نايس ون",           "url": "https://www.niceone.com/ar/offers",              "cat": "جمال",       "emoji": "💄", "bg": "#2a0020", "org": "سعودي",  "desc": "منتجات تجميل سعودية أصيلة بعروض يومية"},
    # بقالة
    {"name": "كارفور السعودية",   "url": "https://www.carrefourksa.com/mafsau/ar/deals",  "cat": "بقالة",      "emoji": "🛒", "bg": "#001a2a", "org": "عالمي",  "desc": "تسوق أسبوعي بأسعار لا تقبل المنافسة"},
    {"name": "بنده",              "url": "https://www.bindawood.com/ar/offers",            "cat": "بقالة",      "emoji": "🥬", "bg": "#002a10", "org": "سعودي",  "desc": "سوبرماركت سعودي بعروض أسبوعية مميزة"},
    {"name": "العثيم",            "url": "https://www.othaim.com.sa/ar/offers",            "cat": "بقالة",      "emoji": "🛍️", "bg": "#001a00", "org": "سعودي",  "desc": "أسواق العثيم السعودية بعروض يومية على البقالة"},
    # منزل
    {"name": "أيكيا السعودية",    "url": "https://www.ikea.com/sa/ar/offers/",            "cat": "منزل",       "emoji": "🛋️", "bg": "#001a2a", "org": "عالمي",  "desc": "أثاث وديكور منزلي بأسعار مثالية وتصاميم عصرية"},
    {"name": "هوم سنتر",          "url": "https://www.homecentre.com/sa-ar/sale",          "cat": "منزل",       "emoji": "🏠", "bg": "#2a1000", "org": "خليجي",  "desc": "مفروشات وأدوات منزلية وديكور بخصومات موسمية"},
    # رياضة
    {"name": "نايكي السعودية",    "url": "https://www.nike.com/sa/w/sale",                "cat": "رياضة",      "emoji": "✔️", "bg": "#001a08", "org": "عالمي",  "desc": "أحذية وملابس رياضية بتخفيضات موسمية كبيرة"},
    {"name": "أديداس السعودية",   "url": "https://www.adidas.com.sa/ar/sale",             "cat": "رياضة",      "emoji": "⚽", "bg": "#00102a", "org": "عالمي",  "desc": "ملابس وأحذية أديداس بأفضل أسعار السعودية"},
    {"name": "ديكاتلون",          "url": "https://www.decathlon.sa/ar/sports-offers/",    "cat": "رياضة",      "emoji": "🏊", "bg": "#001a1a", "org": "عالمي",  "desc": "معدات رياضية متكاملة لجميع الأنشطة بأسعار مناسبة"},
    # صيدلية
    {"name": "النهدي",            "url": "https://www.nahdi.sa/ar/offers",                "cat": "صيدلية",     "emoji": "🏥", "bg": "#001a10", "org": "سعودي",  "desc": "صيدلية سعودية كبرى — منتجات صحية وجمال بعروض أسبوعية"},
    {"name": "إيفا فارما",        "url": "https://www.evapharmacy.com.sa/ar/offers",      "cat": "صيدلية",     "emoji": "💊", "bg": "#002020", "org": "عالمي",  "desc": "مستحضرات طبية وتجميلية بأسعار مناسبة وتوصيل سريع"},
]

# ══════════════════════════════════════════════════════════════════
# وظائف الاستخراج
# ══════════════════════════════════════════════════════════════════

DISCOUNT_RE = re.compile(
    r"(\d{1,3})\s*%\s*(?:off|خصم|تخفيض|discount|وفر|save|حتى|up\s+to)?"
    r"|(?:خصم|تخفيض|off|save|حتى|up\s+to)\s*(\d{1,3})\s*%",
    re.IGNORECASE,
)


def extract_discount(text: str) -> int | None:
    hits = []
    for m in DISCOUNT_RE.finditer(text):
        val = m.group(1) or m.group(2)
        if val:
            n = int(val)
            if 5 <= n <= 95:
                hits.append(n)
    return max(hits) if hits else None


def extract_image(soup: BeautifulSoup, base_url: str) -> str | None:
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        src = str(og["content"])
        return src if src.startswith("http") else urljoin(base_url, src)
    for img in soup.find_all("img", src=True)[:30]:
        src = str(img.get("src", ""))
        if not src or any(k in src.lower() for k in ["logo", "icon", "flag", "avatar"]):
            continue
        try:
            w = int(str(img.get("width") or img.get("data-width") or "0").replace("px", ""))
            if w >= 80:
                return src if src.startswith("http") else urljoin(base_url, src)
        except (ValueError, TypeError):
            pass
    return None


# ══════════════════════════════════════════════════════════════════
# جلب متجر واحد
# ══════════════════════════════════════════════════════════════════

def fetch_site(session: requests.Session, site: dict) -> dict:
    result = {**site}
    url    = site["url"]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info(f"  [{attempt}/{MAX_RETRIES}] {site['name']}")
            resp = session.get(url, headers=HEADERS, timeout=TIMEOUT,
                               allow_redirects=True)

            result["http_status"] = resp.status_code
            result["final_url"]   = resp.url

            if resp.status_code == 404:
                result["active"] = False
                result["error"]  = "404 Not Found"
                return result

            if not resp.ok:
                result["active"] = False
                result["error"]  = f"HTTP {resp.status_code}"
                return result

            soup = BeautifulSoup(resp.text, "html.parser")

            # نحافظ على الخصم الثابت إن وُجد في تعريف المتجر
            result["discount"]     = site.get("discount") or extract_discount(resp.text)
            result["thumbnail"]    = extract_image(soup, url)
            result["active"]       = True
            result["last_updated"] = datetime.now(timezone.utc).isoformat()
            result.pop("error", None)

            log.info(f"  ✅ {site['name']} | discount={result['discount']}%")
            return result

        except requests.Timeout:
            log.warning(f"  ⏱  Timeout (attempt {attempt})")
            time.sleep(DELAY * attempt)
        except requests.ConnectionError as exc:
            result["active"] = False
            result["error"]  = f"Connection error: {exc}"
            return result
        except Exception as exc:
            result["active"] = False
            result["error"]  = str(exc)
            return result

    result["active"] = False
    result["error"]  = "Max retries exceeded"
    return result


# ══════════════════════════════════════════════════════════════════
# التشغيل الرئيسي
# ══════════════════════════════════════════════════════════════════

def run() -> None:
    log.info("=" * 55)
    log.info("🛍️  Saudi Deals Daily — Scraper")
    log.info(f"📁  Output: {SITES_FILE}")
    log.info("=" * 55)

    # تحميل البيانات القديمة للاحتفاظ بها عند الفشل
    old_data: dict[str, dict] = {}
    if SITES_FILE.exists():
        try:
            old = json.loads(SITES_FILE.read_text(encoding="utf-8"))
            old_data = {s["name"]: s for s in old.get("sites", [])}
        except Exception:
            pass

    results = []
    with requests.Session() as session:
        for i, site in enumerate(SITES):
            log.info(f"\n[{i+1}/{len(SITES)}] {site['name']}")
            result = fetch_site(session, site)

            # دمج مع البيانات القديمة عند الفشل
            if not result.get("active") and site["name"] in old_data:
                prev = old_data[site["name"]]
                result.setdefault("discount",     prev.get("discount"))
                result.setdefault("thumbnail",    prev.get("thumbnail"))
                result.setdefault("last_updated", prev.get("last_updated"))

            results.append(result)
            time.sleep(DELAY)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total":        len(results),
        "active":       sum(1 for s in results if s.get("active")),
        "sites":        results,
    }

    SITES_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    log.info("\n" + "=" * 55)
    log.info(f"✅  Done — {output['active']}/{output['total']} active")
    log.info(f"📁  Saved → {SITES_FILE}")
    log.info("=" * 55)


if __name__ == "__main__":
    run()
