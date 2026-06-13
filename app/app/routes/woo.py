from flask import Blueprint, redirect, url_for, flash
from flask_login import login_required
from ..services.woo_sync import push_all_stock

woo_bp = Blueprint('woo', __name__, url_prefix='/woo')


@woo_bp.route('/sync-all', methods=['POST'])
@login_required
def sync_all():
    result = push_all_stock()
    if result['fail'] == 0:
        flash(f"WooCommerce synchronisiert: {result['ok']} Artikel aktualisiert.", 'success')
    else:
        flash(
            f"WooCommerce: {result['ok']} OK, {result['fail']} Fehler "
            f"(Details im Server-Log).",
            'warning'
        )
    return redirect(url_for('reports.stock'))
