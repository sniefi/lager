import os
import logging
from sqlalchemy import text
from ..extensions import db

logger = logging.getLogger(__name__)

WOO_URL    = os.environ.get('WOO_URL', '')
WOO_KEY    = os.environ.get('WOO_CONSUMER_KEY', '')
WOO_SECRET = os.environ.get('WOO_CONSUMER_SECRET', '')

# Schwellen für die 3-Stufen-Anzeige im Shop
THRESHOLD_LOW = int(os.environ.get('WOO_LOW_STOCK_THRESHOLD', '5'))


def _get_main_stock(article_id: int) -> float:
    """Aktuellen Hauptlager-Bestand (Stk) für einen Artikel."""
    row = db.session.execute(text(
        "SELECT COALESCE(stock, 0) AS stock FROM v_stock "
        "WHERE article_id = :aid AND warehouse_type = 'main'"
    ), {'aid': article_id}).fetchone()
    return float(row.stock) if row else 0.0


def push_stock(article) -> bool:
    """
    Schreibt den aktuellen Hauptlager-Bestand des Artikels in WooCommerce.
    Gibt True zurück wenn erfolgreich, False bei Fehler (Buchung bleibt trotzdem gespeichert).
    Tut nichts wenn woo_product_id nicht gesetzt oder WC nicht konfiguriert ist.
    """
    if not article.woo_product_id:
        return True
    if not WOO_URL or not WOO_KEY or not WOO_SECRET:
        logger.warning("WooCommerce nicht konfiguriert (WOO_URL/KEY/SECRET fehlen)")
        return False

    try:
        import requests
        stock_qty = _get_main_stock(article.id)

        if stock_qty <= 0:
            status = 'outofstock'
        elif stock_qty <= THRESHOLD_LOW:
            status = 'instock'  # WC zeigt "Low stock" wenn manage_stock=true und qty <= low_stock_amount
        else:
            status = 'instock'

        url = f"{WOO_URL.rstrip('/')}/wp-json/wc/v3/products/{article.woo_product_id}"
        resp = requests.put(
            url,
            auth=(WOO_KEY, WOO_SECRET),
            json={
                'manage_stock': True,
                'stock_quantity': int(stock_qty),
                'low_stock_amount': THRESHOLD_LOW,
                'stock_status': status,
            },
            timeout=8,
        )
        resp.raise_for_status()
        logger.info("WC sync: Artikel %s (WC-ID %d) → %d Stk", article.name, article.woo_product_id, int(stock_qty))
        return True
    except Exception as exc:
        logger.error("WC sync fehlgeschlagen für Artikel %s: %s", article.name, exc)
        return False


def push_all_stock() -> dict:
    """
    Synchronisiert alle Artikel mit gesetzter woo_product_id.
    Gibt {'ok': n, 'fail': n, 'skipped': n} zurück.
    """
    from ..models.article import Article
    articles = Article.query.filter(Article.woo_product_id.isnot(None), Article.is_active == True).all()
    ok = fail = skipped = 0
    for article in articles:
        if not article.woo_product_id:
            skipped += 1
            continue
        if push_stock(article):
            ok += 1
        else:
            fail += 1
    return {'ok': ok, 'fail': fail, 'skipped': skipped}
