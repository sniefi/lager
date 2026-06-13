import os
import logging
import requests
from sqlalchemy import text
from ..extensions import db

logger = logging.getLogger(__name__)

WOO_URL    = os.environ.get('WOO_URL', '').rstrip('/')
WOO_KEY    = os.environ.get('WOO_CONSUMER_KEY', '')
WOO_SECRET = os.environ.get('WOO_CONSUMER_SECRET', '')


def _get_main_stock(article_id: int) -> float:
    """Aktuellen Hauptlager-Bestand (Stk) für einen Artikel."""
    row = db.session.execute(text(
        "SELECT COALESCE(stock, 0) AS stock FROM v_stock "
        "WHERE article_id = :aid AND warehouse_type = 'main'"
    ), {'aid': article_id}).fetchone()
    return float(row.stock) if row else 0.0


def _wc_put(path: str, body: dict) -> bool:
    """PUT-Request an WooCommerce REST API. Gibt True bei Erfolg zurück."""
    url = f"{WOO_URL}/wp-json/wc/v3/{path}"
    resp = requests.put(url, auth=(WOO_KEY, WOO_SECRET), json=body, timeout=8)
    resp.raise_for_status()
    return True


def _get_variation_ids(product_id: int) -> list[int]:
    """Alle Variations-IDs eines variablen Produkts abrufen."""
    url = f"{WOO_URL}/wp-json/wc/v3/products/{product_id}/variations"
    resp = requests.get(url, auth=(WOO_KEY, WOO_SECRET), params={'per_page': 100}, timeout=8)
    resp.raise_for_status()
    return [v['id'] for v in resp.json()]


def _is_variable(product_id: int) -> bool:
    """Prüft ob ein WC-Produkt vom Typ 'variable' ist."""
    url = f"{WOO_URL}/wp-json/wc/v3/products/{product_id}"
    resp = requests.get(url, auth=(WOO_KEY, WOO_SECRET), timeout=8)
    resp.raise_for_status()
    return resp.json().get('type') == 'variable'


def push_stock(article) -> bool:
    """
    Sendet den Lagerstatus (nur stock_status, keine Menge) an WooCommerce.
    Logik: Bestand > 0 → instock | Bestand ≤ 0 → onbackorder (bleibt kaufbar).
    Bei variablen Produkten wird der Status auf alle Variationen gesetzt.
    Fehler beim WC-Call blockieren die Buchung NICHT (nur Logging).
    """
    if not article.woo_product_id:
        return True
    if not WOO_URL or not WOO_KEY or not WOO_SECRET:
        logger.warning("WooCommerce nicht konfiguriert (WOO_URL/KEY/SECRET fehlen)")
        return False

    try:
        stock = _get_main_stock(article.id)
        status = 'instock' if stock > 0 else 'onbackorder'
        body = {'stock_status': status}

        if _is_variable(article.woo_product_id):
            variation_ids = _get_variation_ids(article.woo_product_id)
            for vid in variation_ids:
                _wc_put(f"products/{article.woo_product_id}/variations/{vid}", body)
            logger.info("WC sync (variable): %s (WC-ID %d, %d Varianten) → %s",
                        article.name, article.woo_product_id, len(variation_ids), status)
        else:
            _wc_put(f"products/{article.woo_product_id}", body)
            logger.info("WC sync: %s (WC-ID %d) → %s", article.name, article.woo_product_id, status)

        return True
    except Exception as exc:
        logger.error("WC sync fehlgeschlagen für %s (WC-ID %d): %s",
                     article.name, article.woo_product_id, exc)
        return False


def push_all_stock() -> dict:
    """
    Synchronisiert alle Artikel mit gesetzter woo_product_id.
    Gibt {'ok': n, 'fail': n} zurück.
    """
    from ..models.article import Article
    articles = Article.query.filter(
        Article.woo_product_id.isnot(None),
        Article.is_active == True
    ).all()
    ok = fail = 0
    for article in articles:
        if push_stock(article):
            ok += 1
        else:
            fail += 1
    return {'ok': ok, 'fail': fail}
