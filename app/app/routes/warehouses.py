from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from ..extensions import db
from ..models.warehouse import Warehouse

warehouses_bp = Blueprint('warehouses', __name__, url_prefix='/warehouses')


@warehouses_bp.route('/')
@login_required
def list():
    warehouses = Warehouse.query.order_by(Warehouse.type, Warehouse.name).all()
    return render_template('warehouses/list.html', warehouses=warehouses)


@warehouses_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()

        if not name:
            flash('Name ist ein Pflichtfeld.', 'danger')
            return render_template('warehouses/form.html')

        if Warehouse.query.filter_by(name=name).first():
            flash(f'Lager „{name}" existiert bereits.', 'danger')
            return render_template('warehouses/form.html')

        warehouse = Warehouse(name=name, type='employee')
        db.session.add(warehouse)
        db.session.commit()
        flash(f'Mitarbeiterlager „{name}" wurde angelegt.', 'success')
        return redirect(url_for('warehouses.list'))

    return render_template('warehouses/form.html')
