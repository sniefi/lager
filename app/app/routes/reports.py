from decimal import Decimal
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from sqlalchemy import text
from ..extensions import db
from ..models.warehouse import Warehouse
from ..models.booking import Booking

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
def index():
    return redirect(url_for('reports.stock'))


def _fifo_value(article_id, warehouse_id, current_stock):
    """
    FIFO-Bewertung: Alle Einkäufe für diesen Artikel (ältester zuerst),
    dann aktuellen Bestand (Stück) von vorne abbauen und Wert summieren.
    Preis pro Stück (aus article.price).
    """
    # Alle Einkaufsbuchungen mit Preis, älteste zuerst
    einkaufe = db.session.execute(text("""
        SELECT b.quantity, a.price
        FROM booking b
        JOIN article a ON a.id = b.article_id
        WHERE b.article_id = :aid
          AND b.booking_type IN ('Einkauf', 'Inventur')
          AND b.target_warehouse_id = :wid
          AND a.price IS NOT NULL
        ORDER BY b.created_at ASC
    """), {'aid': article_id, 'wid': warehouse_id}).fetchall()

    remaining = Decimal(str(current_stock))
    total_value = Decimal('0')

    for row in reversed(einkaufe):  # FIFO: neueste Einkäufe zuerst abbauen
        if remaining <= 0:
            break
        qty = Decimal(str(row.quantity))
        price = Decimal(str(row.price))
        used = min(qty, remaining)
        total_value += used * price
        remaining -= used

    return float(total_value)


@reports_bp.route('/stock')
@login_required
def stock():
    rows = db.session.execute(text("""
        SELECT vs.warehouse_id, vs.warehouse_name, vs.warehouse_type,
               vs.article_id, vs.article_code, vs.article_name, vs.unit, vs.stock,
               a.price
        FROM v_stock vs
        JOIN article a ON a.id = vs.article_id
        WHERE vs.stock != 0
        ORDER BY vs.warehouse_name, vs.article_name
    """)).fetchall()

    warehouses = {}
    for row in rows:
        wid = row.warehouse_id
        if wid not in warehouses:
            warehouses[wid] = {
                'id': wid,
                'name': row.warehouse_name,
                'type': row.warehouse_type,
                'artikel': [],
            }
        stock_val = float(row.stock)
        price = float(row.price) if row.price else None
        # Wert = Bestand × Preis/Stk (einfach), FIFO nur wenn Preis vorhanden
        wert = None
        if price is not None and stock_val > 0:
            wert = _fifo_value(row.article_id, wid, stock_val)

        warehouses[wid]['artikel'].append({
            'article_id': row.article_id,
            'article_code': row.article_code,
            'article_name': row.article_name,
            'unit': row.unit,
            'stock': stock_val,
            'price': price,
            'wert': wert,
        })

    employee_warehouses = Warehouse.query.filter_by(type='employee').order_by(Warehouse.name).all()
    return render_template('reports/stock_overview.html',
                           warehouses=list(warehouses.values()),
                           employee_warehouses=employee_warehouses)


@reports_bp.route('/employee/<int:warehouse_id>')
@login_required
def employee_detail(warehouse_id):
    warehouse = db.get_or_404(Warehouse, warehouse_id)

    unbilled = (Booking.query
                .filter_by(source_warehouse_id=warehouse_id,
                           booking_type='Abgang',
                           abgang_destination='Eigenbedarf',
                           is_billed=0)
                .order_by(Booking.created_at.desc())
                .all())

    billed = (Booking.query
              .filter_by(source_warehouse_id=warehouse_id,
                         booking_type='Abgang',
                         abgang_destination='Eigenbedarf',
                         is_billed=1)
              .order_by(Booking.billed_at.desc())
              .limit(50)
              .all())

    return render_template('reports/employee_detail.html',
                           warehouse=warehouse,
                           unbilled=unbilled,
                           billed=billed)


@reports_bp.route('/employee/<int:warehouse_id>/bill/<int:booking_id>', methods=['POST'])
@login_required
def toggle_billed(warehouse_id, booking_id):
    booking = db.get_or_404(Booking, booking_id)
    if booking.is_billed:
        booking.is_billed = 0
        booking.billed_at = None
    else:
        booking.is_billed = 1
        booking.billed_at = datetime.utcnow()
    db.session.commit()
    return '', 200


@reports_bp.route('/outgoing')
@login_required
def outgoing():
    year = request.args.get('year', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    booking_type_filter = request.args.get('booking_type', '')
    customer = request.args.get('customer', '')

    query = Booking.query.filter(Booking.booking_type.in_(['Abgang', 'Umlagerung']))

    if year:
        query = query.filter(db.func.year(Booking.created_at) == year)
    if warehouse_id:
        query = query.filter(Booking.source_warehouse_id == warehouse_id)
    if booking_type_filter:
        query = query.filter(Booking.booking_type == booking_type_filter)
    if customer:
        query = query.filter(Booking.customer_name.ilike(f'%{customer}%'))

    bookings = query.order_by(Booking.created_at.desc()).all()
    warehouses = Warehouse.query.order_by(Warehouse.name).all()

    years_result = db.session.execute(text(
        "SELECT DISTINCT YEAR(created_at) AS yr FROM booking "
        "WHERE booking_type IN ('Abgang', 'Umlagerung') ORDER BY yr DESC"
    ))
    years = [row.yr for row in years_result]

    # Alle distinkten Kundennamen für Dropdown
    customers_result = db.session.execute(text(
        "SELECT DISTINCT customer_name FROM booking "
        "WHERE customer_name IS NOT NULL AND customer_name != '' "
        "ORDER BY customer_name"
    ))
    all_customers = [r.customer_name for r in customers_result]

    return render_template('reports/outgoing_report.html',
                           bookings=bookings,
                           warehouses=warehouses,
                           years=years,
                           all_customers=all_customers,
                           selected_year=year,
                           selected_warehouse=warehouse_id,
                           selected_type=booking_type_filter,
                           selected_customer=customer)
