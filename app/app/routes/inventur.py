from collections import defaultdict
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from ..extensions import db
from ..models.booking import Booking
from ..models.warehouse import Warehouse
from ..models.inventur import Inventur, InventurPosition

inventur_bp = Blueprint('inventur', __name__, url_prefix='/inventur')


@inventur_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    main_warehouse = Warehouse.query.filter_by(type='main').first()
    if not main_warehouse:
        flash('Hauptlager nicht gefunden.', 'danger')
        return redirect(url_for('reports.stock'))

    # Alle aktiven Artikel mit aktuellem Hauptlager-Bestand
    rows = db.session.execute(text("""
        SELECT a.id, a.article_id, a.name, a.unit, a.price,
               COALESCE(s.stock, 0) AS stock
        FROM article a
        LEFT JOIN v_stock s ON s.article_id = a.id AND s.warehouse_id = :wid
        WHERE a.is_active = 1
        ORDER BY a.article_id
    """), {'wid': main_warehouse.id}).fetchall()

    if request.method == 'POST':
        changes = []

        for row in rows:
            val = request.form.get(f'qty_{row.id}', '').strip().replace(',', '.')
            if val == '':
                continue
            try:
                new_qty = Decimal(val)
            except InvalidOperation:
                flash(f'Ungültiger Wert bei „{row.name}".', 'danger')
                return render_template('inventur/inventur.html',
                                       rows=rows, warehouse=main_warehouse)

            if new_qty < 0:
                flash(f'Negative Werte nicht erlaubt bei „{row.name}".', 'danger')
                return render_template('inventur/inventur.html',
                                       rows=rows, warehouse=main_warehouse)

            current = Decimal(str(row.stock))
            diff = new_qty - current
            if diff != 0:
                changes.append({
                    'db_id': row.id,
                    'name': row.name,
                    'qty_before': current,
                    'qty_after': new_qty,
                    'diff': diff,
                })

        if not changes:
            flash('Keine Änderungen erkannt – Inventur nicht gebucht.', 'info')
            return render_template('inventur/inventur.html',
                                   rows=rows, warehouse=main_warehouse)

        # Inventur-Kopf anlegen
        inv = Inventur()
        db.session.add(inv)
        db.session.flush()

        for c in changes:
            # Bestandskorrektur als Inventur-Buchung
            if c['diff'] > 0:
                booking = Booking(
                    booking_type='Inventur',
                    article_id=c['db_id'],
                    quantity=c['diff'],
                    target_warehouse_id=main_warehouse.id,
                )
            else:
                booking = Booking(
                    booking_type='Inventur',
                    article_id=c['db_id'],
                    quantity=abs(c['diff']),
                    source_warehouse_id=main_warehouse.id,
                )
            db.session.add(booking)

            pos = InventurPosition(
                inventur_id=inv.id,
                article_id=c['db_id'],
                warehouse_id=main_warehouse.id,
                quantity_before=c['qty_before'],
                quantity_after=c['qty_after'],
                difference=c['diff'],
            )
            db.session.add(pos)

        db.session.commit()
        flash(f'Inventur #{inv.id} gebucht – {len(changes)} Position(en) angepasst.', 'success')
        return redirect(url_for('inventur.report'))

    return render_template('inventur/inventur.html',
                           rows=rows, warehouse=main_warehouse)


@inventur_bp.route('/report')
@login_required
def report():
    year = request.args.get('year', type=int)

    rows = db.session.execute(text("""
        SELECT
            inv.id          AS inv_id,
            inv.created_at  AS inv_date,
            a.article_id    AS article_code,
            a.name          AS article_name,
            a.unit          AS unit,
            a.price         AS price,
            ip.quantity_before,
            ip.quantity_after,
            ip.difference
        FROM inventur inv
        JOIN inventur_position ip ON ip.inventur_id = inv.id
        JOIN article a ON a.id = ip.article_id
        WHERE (:year IS NULL OR YEAR(inv.created_at) = :year)
        ORDER BY inv.created_at DESC, a.article_id
    """), {'year': year}).fetchall()

    # Gruppieren nach Inventur
    groups_map = defaultdict(list)
    group_dates = {}
    for r in rows:
        groups_map[r.inv_id].append(r)
        group_dates[r.inv_id] = r.inv_date

    grouped = sorted(
        [{'inv_id': k, 'inv_date': group_dates[k], 'positions': v}
         for k, v in groups_map.items()],
        key=lambda g: g['inv_date'],
        reverse=True
    )

    # Verfügbare Jahre
    years_result = db.session.execute(text(
        "SELECT DISTINCT YEAR(created_at) AS yr FROM inventur ORDER BY yr DESC"
    ))
    years = [r.yr for r in years_result]

    return render_template('inventur/report.html',
                           grouped=grouped,
                           years=years,
                           selected_year=year)
