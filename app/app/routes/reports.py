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


@reports_bp.route('/stock')
@login_required
def stock():
    rows = db.session.execute(text("""
        SELECT warehouse_id, warehouse_name, warehouse_type,
               article_id, article_code, article_name, unit, stock
        FROM v_stock
        WHERE stock != 0
        ORDER BY warehouse_name, article_name
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
        warehouses[wid]['artikel'].append({
            'article_id': row.article_id,
            'article_code': row.article_code,
            'article_name': row.article_name,
            'unit': row.unit,
            'stock': float(row.stock),
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
    return '', 200  # HTMX entfernt die Zeile


@reports_bp.route('/outgoing')
@login_required
def outgoing():
    year = request.args.get('year', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    booking_type_filter = request.args.get('booking_type', '')
    customer = request.args.get('customer', '')

    query = Booking.query.filter(Booking.booking_type.in_(['Abgang', 'Umlagerung']))

    if year:
        query = query.filter(
            db.func.year(Booking.created_at) == year
        )
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

    return render_template('reports/outgoing_report.html',
                           bookings=bookings,
                           warehouses=warehouses,
                           years=years,
                           selected_year=year,
                           selected_warehouse=warehouse_id,
                           selected_type=booking_type_filter,
                           selected_customer=customer)
