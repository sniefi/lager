from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from ..extensions import db
from ..models.article import Article

articles_bp = Blueprint('articles', __name__, url_prefix='/articles')


@articles_bp.route('/')
@login_required
def list():
    articles = Article.query.order_by(Article.article_id).all()
    return render_template('articles/list.html', articles=articles)


@articles_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        article_id = request.form.get('article_id', '').strip()
        name = request.form.get('name', '').strip()
        unit = request.form.get('unit', 'Liter').strip() or 'Liter'
        price_str = request.form.get('price', '').replace(',', '.')

        if not article_id or not name:
            flash('Artikelcode und Name sind Pflichtfelder.', 'danger')
            return render_template('articles/form.html')

        if Article.query.filter_by(article_id=article_id).first():
            flash(f'Artikelcode „{article_id}" existiert bereits.', 'danger')
            return render_template('articles/form.html')

        price = None
        if price_str:
            try:
                price = float(price_str)
            except ValueError:
                flash('Ungültiger Preis.', 'danger')
                return render_template('articles/form.html')

        article = Article(article_id=article_id, name=name, unit=unit, price=price)
        db.session.add(article)
        db.session.commit()
        flash(f'Artikel „{name}" wurde angelegt.', 'success')
        return redirect(url_for('articles.list'))

    return render_template('articles/form.html')


@articles_bp.route('/<int:pk>/edit', methods=['GET', 'POST'])
@login_required
def edit(pk):
    article = db.get_or_404(Article, pk)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        unit = request.form.get('unit', 'Liter').strip() or 'Liter'
        price_str = request.form.get('price', '').replace(',', '.')

        if not name:
            flash('Name ist Pflichtfeld.', 'danger')
            return render_template('articles/edit.html', article=article)

        price = None
        if price_str:
            try:
                price = float(price_str)
            except ValueError:
                flash('Ungültiger Preis.', 'danger')
                return render_template('articles/edit.html', article=article)

        article.name = name
        article.unit = unit
        article.price = price
        db.session.commit()
        flash(f'Artikel „{article.name}" wurde gespeichert.', 'success')
        return redirect(url_for('articles.list'))

    return render_template('articles/edit.html', article=article)


@articles_bp.route('/<int:pk>/toggle-active', methods=['POST'])
@login_required
def toggle_active(pk):
    article = db.get_or_404(Article, pk)
    article.is_active = not article.is_active
    db.session.commit()
    status = 'aktiviert' if article.is_active else 'deaktiviert'
    flash(f'Artikel „{article.name}" wurde {status}.', 'success' if article.is_active else 'warning')
    return redirect(url_for('articles.edit', pk=pk))
