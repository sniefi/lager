from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from ..extensions import db
from ..models.article import Article
from ..models.warehouse import Warehouse
from ..models.booking import Booking
from ..services.woo_sync import push_stock

bookings_bp = Blueprint('bookings', __name__, url_prefix='/bookings')


def _get_stock(article_id, warehouse_id):
    """Aktuellen Bestand eines Artikels in einem Lager aus v_stock."""
    row = db.session.execute(text(
        "SELECT COALESCE(stock, 0) AS stock FROM v_stock "
        "WHERE article_id = :aid AND warehouse_id = :wid"
    ), {'aid': article_id, 'wid': warehouse_id}).fetchone()
    return float(row.stock) if row else 0.0


@bookings_bp.route('/incoming', methods=['GET', 'POST'])
@login_required
def incoming():
    articles = Article.query.filter_by(is_active=True).order_by(Article.article_id).all()

    if request.method == 'POST':
        article_code = request.form.get('article_code', '').strip()
        quantity_str = request.form.get('quantity', '').replace(',', '.')

        article = Article.query.filter_by(article_id=article_code, is_active=True).first()
        if not article:
            flash(f'Artikel „{article_code}" nicht gefunden oder inaktiv.', 'danger')
            return render_template('bookings/incoming.html', articles=articles)

        try:
            quantity = float(quantity_str)
        except ValueError:
            flash('Ungültige Mengenangabe.', 'danger')
            return render_template('bookings/incoming.html', articles=articles)

        if quantity <= 0:
            flash('Menge muss größer als 0 sein.', 'danger')
            return render_template('bookings/incoming.html', articles=articles)

        main_warehouse = Warehouse.query.filter_by(type='main').first()
        if not main_warehouse:
            flash('Hauptlager nicht gefunden.', 'danger')
            return render_template('bookings/incoming.html', articles=articles)

        booking = Booking(
            booking_type='Einkauf',
            article_id=article.id,
            quantity=quantity,
            target_warehouse_id=main_warehouse.id,
        )
        db.session.add(booking)
        db.session.commit()
        push_stock(article)
        flash(f'Einkauf: {quantity:g} Stk „{article.name}" eingelagert.', 'success')
        return redirect(url_for('bookings.incoming'))

    return render_template('bookings/incoming.html', articles=articles)


@bookings_bp.route('/outgoing', methods=['GET', 'POST'])
@login_required
def outgoing():
    articles = Article.query.filter_by(is_active=True).order_by(Article.article_id).all()
    warehouses = Warehouse.query.order_by(Warehouse.type, Warehouse.name).all()
    employee_warehouses = [w for w in warehouses if w.type == 'employee']
    main_warehouse = next((w for w in warehouses if w.type == 'main'), None)

    # Pre-fill aus URL-Parametern (z.B. von Lagerstand-Buttons)
    prefill = {
        'article_code': request.args.get('article_code', ''),
        'booking_type': request.args.get('booking_type', ''),
        'source_warehouse_id': request.args.get('source_warehouse_id', type=int),
        'destination': request.args.get('destination', ''),
    }
    prefill_article = None
    if prefill['article_code']:
        prefill_article = Article.query.filter_by(article_id=prefill['article_code']).first()

    if request.method == 'POST':
        booking_type = request.form.get('booking_type', '')
        article_code = request.form.get('article_code', '').strip()
        quantity_str = request.form.get('quantity', '').replace(',', '.')
        source_warehouse_id = request.form.get('source_warehouse_id', type=int)
        abgang_destination = request.form.get('abgang_destination', '')
        customer_name = request.form.get('customer_name', '').strip()
        abgang_grund = request.form.get('abgang_grund', '').strip()
        target_warehouse_id = request.form.get('target_warehouse_id', type=int)

        ctx = dict(articles=articles, warehouses=warehouses,
                   employee_warehouses=employee_warehouses, main_warehouse=main_warehouse,
                   prefill={}, prefill_article=None)

        article = Article.query.filter_by(article_id=article_code).first()
        if not article:
            flash(f'Artikel „{article_code}" nicht gefunden.', 'danger')
            return render_template('bookings/outgoing.html', **ctx)

        try:
            quantity = float(quantity_str)
        except ValueError:
            flash('Ungültige Mengenangabe.', 'danger')
            return render_template('bookings/outgoing.html', **ctx)

        if quantity <= 0:
            flash('Menge muss größer als 0 sein.', 'danger')
            return render_template('bookings/outgoing.html', **ctx)

        if booking_type == 'Abgang':
            if not source_warehouse_id:
                flash('Ausgangslager ist Pflichtfeld.', 'danger')
                return render_template('bookings/outgoing.html', **ctx)
            if not abgang_destination:
                flash('Abgangsart ist Pflichtfeld.', 'danger')
                return render_template('bookings/outgoing.html', **ctx)
            if abgang_destination == 'Kunde' and not customer_name:
                flash('Kundenname ist Pflichtfeld bei Abgang an Kunden.', 'danger')
                return render_template('bookings/outgoing.html', **ctx)
            if abgang_destination == 'Kunde' and not abgang_grund:
                flash('Grund ist Pflichtfeld bei Abgang an Kunden.', 'danger')
                return render_template('bookings/outgoing.html', **ctx)

            # Negativbestand verhindern
            current_stock = _get_stock(article.id, source_warehouse_id)
            if quantity > current_stock:
                wh = Warehouse.query.get(source_warehouse_id)
                wh_name = wh.name if wh else 'Lager'
                flash(
                    f'Nicht genug Bestand in „{wh_name}". '
                    f'Verfügbar: {current_stock:g} Stk – angefordert: {quantity:g} Stk.',
                    'danger'
                )
                return render_template('bookings/outgoing.html', **ctx)

            booking = Booking(
                booking_type='Abgang',
                article_id=article.id,
                quantity=quantity,
                source_warehouse_id=source_warehouse_id,
                abgang_destination=abgang_destination,
                customer_name=customer_name if abgang_destination == 'Kunde' else None,
                abgang_grund=abgang_grund if abgang_destination == 'Kunde' else None,
            )

        elif booking_type == 'Umlagerung':
            if not target_warehouse_id:
                flash('Ziellager ist Pflichtfeld.', 'danger')
                return render_template('bookings/outgoing.html', **ctx)
            if not main_warehouse:
                flash('Hauptlager nicht gefunden.', 'danger')
                return render_template('bookings/outgoing.html', **ctx)

            # Negativbestand im Hauptlager verhindern
            current_stock = _get_stock(article.id, main_warehouse.id)
            if quantity > current_stock:
                flash(
                    f'Nicht genug Bestand im Hauptlager. '
                    f'Verfügbar: {current_stock:g} Stk – angefordert: {quantity:g} Stk.',
                    'danger'
                )
                return render_template('bookings/outgoing.html', **ctx)

            booking = Booking(
                booking_type='Umlagerung',
                article_id=article.id,
                quantity=quantity,
                source_warehouse_id=main_warehouse.id,
                target_warehouse_id=target_warehouse_id,
            )
        else:
            flash('Ungültiger Buchungstyp.', 'danger')
            return render_template('bookings/outgoing.html', **ctx)

        db.session.add(booking)
        db.session.commit()
        push_stock(article)
        flash(f'{booking_type}: {quantity:g} Stk „{article.name}" gebucht.', 'success')
        return redirect(url_for('bookings.outgoing'))

    return render_template('bookings/outgoing.html',
                           articles=articles,
                           warehouses=warehouses,
                           employee_warehouses=employee_warehouses,
                           main_warehouse=main_warehouse,
                           prefill=prefill,
                           prefill_article=prefill_article)


# HTMX: Bedingte Felder je nach Buchungsart
@bookings_bp.route('/type-fields')
@login_required
def type_fields():
    booking_type = request.args.get('booking_type', '')
    prefill_source = request.args.get('source_warehouse_id', type=int)
    prefill_destination = request.args.get('destination', '')
    warehouses = Warehouse.query.order_by(Warehouse.type, Warehouse.name).all()
    employee_warehouses = [w for w in warehouses if w.type == 'employee']
    main_warehouse = next((w for w in warehouses if w.type == 'main'), None)
    return render_template('bookings/_type_fields.html',
                           booking_type=booking_type,
                           warehouses=warehouses,
                           employee_warehouses=employee_warehouses,
                           main_warehouse=main_warehouse,
                           prefill_source=prefill_source,
                           prefill_destination=prefill_destination)


# HTMX: Kundenname-Feld
@bookings_bp.route('/destination-fields')
@login_required
def destination_fields():
    abgang_destination = request.args.get('abgang_destination', '')
    return render_template('bookings/_destination_fields.html',
                           abgang_destination=abgang_destination)


# HTMX API: Artikel-Autocomplete (Dropdown)
@bookings_bp.route('/api/articles/search')
@login_required
def article_search():
    q = request.args.get('q', '')
    if not q:
        return ''
    articles = Article.query.filter(
        Article.is_active == True,
        db.or_(
            Article.article_id.ilike(f'%{q}%'),
            Article.name.ilike(f'%{q}%'),
        )
    ).order_by(Article.article_id).limit(15).all()
    return render_template('bookings/_article_dropdown.html', articles=articles)


# HTMX API: Kunden-Autocomplete
@bookings_bp.route('/api/customers/search')
@login_required
def customer_search():
    q = request.args.get('q', '') or request.args.get('customer_name', '')
    result = db.session.execute(
        text("SELECT DISTINCT customer_name FROM booking WHERE customer_name LIKE :q AND customer_name IS NOT NULL ORDER BY customer_name LIMIT 10"),
        {'q': f'%{q}%'}
    )
    customers = [row.customer_name for row in result]
    return render_template('bookings/_customer_options.html', customers=customers)
