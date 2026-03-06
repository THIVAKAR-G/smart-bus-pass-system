from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from functools import wraps
import stripe
import os
import json
import re
import qrcode
import base64
from io import BytesIO
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, extract

from config import Config
from database import db, User, BusPass, Trip, Payment

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

stripe.api_key = app.config['STRIPE_SECRET_KEY']

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


def _admin_base_metrics():
    total_users = User.query.count()
    total_passes = BusPass.query.count()
    total_revenue = db.session.query(db.func.sum(BusPass.price)).scalar() or 0
    return {
        'total_users': total_users,
        'total_passes': total_passes,
        'total_revenue': round(total_revenue, 2),
    }


@app.context_processor
def inject_admin_context():
    if not session.get('is_admin'):
        return {}

    admin_name = session.get('admin_name', 'System Admin')
    initials = ''.join([part[0] for part in admin_name.split()[:2]]).upper() or 'AD'
    data = _admin_base_metrics()
    data.update({
        'admin_name': admin_name,
        'admin_initials': initials,
    })
    return data


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Please login to access admin module.', 'warning')
            return redirect(url_for('admin_login', next=request.path))
        return fn(*args, **kwargs)
    return wrapper


def _build_pass_export_pdf(passes, report_title='SmartBus Pass Export Report'):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=19,
        textColor=colors.white,
        alignment=1,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#d3e2ff'),
        alignment=1,
        spaceAfter=8
    )
    normal_style = ParagraphStyle(
        'ReportNormal',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1f2d3d')
    )
    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        textColor=colors.white,
        leading=10
    )
    body_cell_style = ParagraphStyle(
        'BodyCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#1f2d3d'),
        leading=10
    )

    story = []
    page_width = landscape(A4)[0] - (doc.leftMargin + doc.rightMargin)
    header_block = Table(
        [[
            Paragraph(report_title, title_style)
        ], [
            Paragraph(
                f'Generated on {datetime.utcnow().strftime("%d %b %Y %H:%M UTC")} | Total Passes: {len(passes)}',
                subtitle_style
            )
        ]],
        colWidths=[page_width]
    )
    header_block.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#143f7c')),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(header_block)
    story.append(Spacer(1, 8))

    if not passes:
        story.append(Paragraph('No pass data found for selected filter.', normal_style))
        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    data = [[
        Paragraph('Pass ID', header_cell_style),
        Paragraph('User', header_cell_style),
        Paragraph('Route', header_cell_style),
        Paragraph('Type', header_cell_style),
        Paragraph('Status', header_cell_style),
        Paragraph('Start', header_cell_style),
        Paragraph('End', header_cell_style),
        Paragraph('Price (INR)', header_cell_style),
        Paragraph('Auto Renew', header_cell_style),
    ]]
    for p in passes:
        data.append([
            Paragraph(str(p.id), body_cell_style),
            Paragraph(p.user.full_name, body_cell_style),
            Paragraph(p.route, body_cell_style),
            Paragraph(p.pass_type.title(), body_cell_style),
            Paragraph(p.status.title(), body_cell_style),
            Paragraph(p.start_date.strftime('%d %b %Y'), body_cell_style),
            Paragraph(p.end_date.strftime('%d %b %Y'), body_cell_style),
            Paragraph(f'{p.price:.2f}', body_cell_style),
            Paragraph('Yes' if p.auto_renew else 'No', body_cell_style)
        ])

    col_widths = [16 * mm, 30 * mm, 74 * mm, 20 * mm, 20 * mm, 24 * mm, 24 * mm, 26 * mm, 22 * mm]
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#133e7c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#b8c8e0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f5f9ff'), colors.HexColor('#ffffff')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        'Confidential: SmartBus internal report. Do not share outside authorized operations.',
        ParagraphStyle('FooterNote', parent=styles['Italic'], fontSize=8, textColor=colors.HexColor('#6f8199'))
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Check email and password.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        phone = (request.form.get('phone') or '').strip()
        user_type = (request.form.get('user_type') or '').strip()
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        confirm_password = request.form.get('confirm_password') or ''
        address = (request.form.get('address') or '').strip()

        if not all([full_name, email, phone, user_type, username, password]):
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('That email is already registered. Please sign in.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('That username is already taken. Please choose another one.', 'danger')
            return redirect(url_for('register'))

        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(
                username=username,
                email=email,
                password=hashed_password,
                full_name=full_name,
                phone=phone,
                address=address,
                user_type=user_type
            )
            
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Account could not be created. Email or username already exists.', 'danger')
            return redirect(url_for('register'))
        except Exception:
            db.session.rollback()
            flash('Something went wrong while creating your account. Please try again.', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['is_admin'] = True
            session['admin_name'] = 'System Administrator'
            flash('Admin login successful.', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin_dashboard'))

        flash('Invalid admin credentials.', 'danger')

    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    session.pop('admin_name', None)
    flash('Admin logged out.', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_home():
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    metrics = _admin_base_metrics()
    recent_users = User.query.order_by(User.created_at.desc()).limit(8).all()
    recent_passes = BusPass.query.order_by(BusPass.created_at.desc()).limit(10).all()

    route_rows = db.session.query(
        BusPass.route.label('route'),
        db.func.count(BusPass.id).label('booked'),
        db.func.sum(BusPass.price).label('revenue')
    ).group_by(BusPass.route).order_by(db.desc('booked')).limit(10).all()

    pass_status_rows = db.session.query(
        BusPass.status.label('status'),
        db.func.count(BusPass.id).label('count')
    ).group_by(BusPass.status).all()

    # Convert SQLAlchemy Row objects into JSON-safe dicts for template charts.
    route_stats = [
        {'route': row.route, 'booked': int(row.booked or 0), 'revenue': float(row.revenue or 0)}
        for row in route_rows
    ]
    pass_status_stats = [
        {'status': row.status, 'count': int(row.count or 0)}
        for row in pass_status_rows
    ]

    return render_template(
        'admin/dashboard.html',
        recent_users=recent_users,
        recent_passes=recent_passes,
        route_stats=route_stats,
        pass_status_stats=pass_status_stats,
        **metrics
    )


@app.route('/admin/users')
@admin_required
def admin_users():
    search = (request.args.get('q') or '').strip()
    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.full_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%')
            )
        )
    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, search=search)


@app.route('/admin/passes')
@admin_required
def admin_passes():
    search = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or '').strip().lower()

    query = BusPass.query.join(User)
    if search:
        query = query.filter(
            db.or_(
                BusPass.route.ilike(f'%{search}%'),
                User.full_name.ilike(f'%{search}%'),
                db.cast(BusPass.id, db.String).ilike(f'%{search}%')
            )
        )
    if status:
        query = query.filter(BusPass.status == status)

    passes = query.order_by(BusPass.created_at.desc()).all()
    return render_template('admin/passes.html', passes=passes, search=search, selected_status=status)


@app.route('/admin/trips')
@admin_required
def admin_trips():
    trips = Trip.query.order_by(Trip.timestamp.desc()).limit(200).all()
    return render_template('admin/trips.html', trips=trips)


@app.route('/admin/payments')
@admin_required
def admin_payments():
    payments = Payment.query.order_by(Payment.timestamp.desc()).limit(200).all()
    return render_template('admin/payments.html', payments=payments)


@app.route('/admin/reports')
@admin_required
def admin_reports():
    route_rows = db.session.query(
        BusPass.route.label('route'),
        db.func.count(BusPass.id).label('booked'),
        db.func.sum(BusPass.price).label('revenue')
    ).group_by(BusPass.route).order_by(db.desc('booked')).all()
    route_stats = [
        {'route': row.route, 'booked': int(row.booked or 0), 'revenue': float(row.revenue or 0)}
        for row in route_rows
    ]
    return render_template('admin/reports.html', route_stats=route_stats)


@app.route('/admin/export-passes', methods=['GET', 'POST'])
@admin_required
def admin_export_passes():
    status_filter = (request.form.get('status') if request.method == 'POST' else request.args.get('status') or '').strip().lower()
    route_filter = (request.form.get('route') if request.method == 'POST' else request.args.get('route') or '').strip()
    recipient_email = (request.form.get('recipient_email') if request.method == 'POST' else '') or 'thivakardixit@gmail.com'
    recipient_email = recipient_email.strip()

    base_query = BusPass.query.join(User)
    if status_filter:
        base_query = base_query.filter(BusPass.status == status_filter)
    if route_filter:
        base_query = base_query.filter(BusPass.route.ilike(f'%{route_filter}%'))

    passes = base_query.order_by(BusPass.created_at.desc()).all()

    distinct_routes = [
        row[0] for row in db.session.query(BusPass.route).distinct().order_by(BusPass.route).all() if row[0]
    ]

    if request.method == 'POST':
        if not recipient_email:
            flash('Recipient email is required.', 'danger')
            return redirect(url_for('admin_export_passes'))

        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            flash('Mail settings are missing. Set MAIL_USERNAME and MAIL_PASSWORD in environment.', 'danger')
            return redirect(url_for('admin_export_passes'))

        try:
            pdf_bytes = _build_pass_export_pdf(passes, report_title='SmartBus Pass Details Export')
            timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
            filename = f'smartbus-pass-export-{timestamp}.pdf'

            msg = Message(
                subject='SmartBus | Official Pass Export Report',
                recipients=[recipient_email],
                sender=app.config.get('MAIL_USERNAME')
            )
            msg.html = f"""
                <div style="font-family:Segoe UI,Arial,sans-serif;background:#f4f8ff;padding:24px;">
                  <div style="max-width:720px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #dbe7ff;">
                    <div style="background:linear-gradient(120deg,#10366b,#1f63be);padding:20px 24px;color:#fff;">
                      <h2 style="margin:0;font-size:24px;">SmartBus Operations</h2>
                      <p style="margin:6px 0 0;font-size:13px;opacity:.9;">Official Export Delivery</p>
                    </div>
                    <div style="padding:24px;color:#1f2d3d;">
                      <p style="margin-top:0;">Hello Team,</p>
                      <p>Please find attached the requested <strong>Pass Details Export</strong> report.</p>
                      <table style="width:100%;border-collapse:collapse;margin:14px 0 18px;">
                        <tr><td style="padding:8px;border-bottom:1px solid #ecf2ff;color:#5c7090;">Generated</td><td style="padding:8px;border-bottom:1px solid #ecf2ff;"><strong>{datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}</strong></td></tr>
                        <tr><td style="padding:8px;border-bottom:1px solid #ecf2ff;color:#5c7090;">Total Records</td><td style="padding:8px;border-bottom:1px solid #ecf2ff;"><strong>{len(passes)}</strong></td></tr>
                        <tr><td style="padding:8px;border-bottom:1px solid #ecf2ff;color:#5c7090;">Status Filter</td><td style="padding:8px;border-bottom:1px solid #ecf2ff;"><strong>{status_filter or 'All'}</strong></td></tr>
                        <tr><td style="padding:8px;color:#5c7090;">Route Filter</td><td style="padding:8px;"><strong>{route_filter or 'All'}</strong></td></tr>
                      </table>
                      <p style="margin-bottom:0;">Regards,<br><strong>SmartBus Admin Module</strong></p>
                    </div>
                    <div style="background:#f0f5ff;padding:14px 24px;font-size:12px;color:#6a7f9e;">
                      Confidential operational email from SmartBus.
                    </div>
                  </div>
                </div>
            """
            msg.attach(filename, 'application/pdf', pdf_bytes)
            mail.send(msg)
            flash(f'Pass report emailed successfully to {recipient_email}.', 'success')
            return redirect(url_for('admin_export_passes'))
        except Exception as exc:
            flash(f'Failed to send email: {exc}', 'danger')
            return redirect(url_for('admin_export_passes'))

    return render_template(
        'admin/export-passes.html',
        recipient_email=recipient_email,
        status_filter=status_filter,
        route_filter=route_filter,
        total_records=len(passes),
        distinct_routes=distinct_routes
    )


@app.route('/admin/activities')
@admin_required
def admin_activities():
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_passes = BusPass.query.order_by(BusPass.created_at.desc()).limit(5).all()
    recent_trips = Trip.query.order_by(Trip.timestamp.desc()).limit(5).all()
    return render_template(
        'admin/activities.html',
        recent_users=recent_users,
        recent_passes=recent_passes,
        recent_trips=recent_trips
    )


@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        admin_name = (request.form.get('admin_name') or '').strip()
        if admin_name:
            session['admin_name'] = admin_name
            flash('Admin profile updated.', 'success')
        return redirect(url_for('admin_settings'))
    return render_template('admin/settings.html')


@app.route('/admin/route-stats')
@admin_required
def admin_route_stats():
    route_rows = db.session.query(
        BusPass.route.label('route'),
        db.func.count(BusPass.id).label('booked'),
        db.func.sum(BusPass.price).label('revenue')
    ).group_by(BusPass.route).order_by(db.desc('booked')).all()
    route_stats = [
        {'route': row.route, 'booked': int(row.booked or 0), 'revenue': float(row.revenue or 0)}
        for row in route_rows
    ]
    return render_template('admin/route-stats.html', route_stats=route_stats)


@app.route('/admin/search')
@admin_required
def admin_search():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'users': [], 'passes': []})

    users = User.query.filter(
        db.or_(
            User.full_name.ilike(f'%{q}%'),
            User.email.ilike(f'%{q}%')
        )
    ).limit(5).all()

    passes = BusPass.query.filter(
        db.or_(
            BusPass.route.ilike(f'%{q}%'),
            db.cast(BusPass.id, db.String).ilike(f'%{q}%')
        )
    ).limit(5).all()

    return jsonify({
        'users': [{'id': u.id, 'name': u.full_name, 'email': u.email} for u in users],
        'passes': [{'id': p.id, 'route': p.route, 'status': p.status} for p in passes]
    })


@app.route('/admin/notifications')
@admin_required
def admin_notifications():
    now = datetime.utcnow()
    expiring_count = BusPass.query.filter(
        BusPass.status == 'active',
        BusPass.end_date <= now + timedelta(days=3),
        BusPass.end_date >= now
    ).count()
    pending_payments = Payment.query.filter_by(status='pending').count()
    return jsonify({'count': expiring_count + pending_payments})

@app.route('/dashboard')
@login_required
def dashboard():
    user_passes = BusPass.query.filter_by(user_id=current_user.id).order_by(BusPass.created_at.desc()).all()
    active_passes = []
    pass_status_counts = {'active': 0, 'expired': 0, 'cancelled': 0}
    today_utc = datetime.utcnow().date()
    qr_updated = False
    status_updated = False

    for bus_pass in user_passes:
        if bus_pass.end_date and bus_pass.end_date.date() < today_utc and bus_pass.status == 'active':
            bus_pass.status = 'expired'
            status_updated = True

        if bus_pass.status not in pass_status_counts:
            pass_status_counts[bus_pass.status] = 0
        pass_status_counts[bus_pass.status] += 1

        if bus_pass.status == 'active':
            previous_qr = bus_pass.qr_code
            bus_pass.generate_qr()
            if bus_pass.qr_code != previous_qr:
                qr_updated = True
            active_passes.append(bus_pass)

    if qr_updated or status_updated:
        db.session.commit()

    active_passes = sorted(active_passes, key=lambda p: p.end_date)
    primary_pass = active_passes[0] if active_passes else None
    days_left = max((primary_pass.end_date.date() - today_utc).days, 0) if primary_pass else 0

    recent_trips = Trip.query.filter_by(user_id=current_user.id).order_by(Trip.timestamp.desc()).limit(8).all()
    total_trips = Trip.query.filter_by(user_id=current_user.id).count()
    total_trip_spent = db.session.query(db.func.sum(Trip.fare)).filter_by(user_id=current_user.id).scalar() or 0
    active_pass_total_amount = sum(p.price for p in active_passes)

    return render_template(
        'dashboard.html',
        active_pass=primary_pass,
        active_passes=active_passes,
        recent_trips=recent_trips,
        total_trips=total_trips,
        total_trip_spent=round(total_trip_spent, 2),
        active_pass_total_amount=round(active_pass_total_amount, 2),
        days_left=days_left,
        pass_status_counts=pass_status_counts
    )

@app.route('/apply-pass', methods=['GET', 'POST'])
@login_required
def apply_pass():
    if request.method == 'POST':
        pass_type = (request.form.get('pass_type') or '').strip().lower()
        price_raw = request.form.get('price')
        route = (request.form.get('route') or '').strip()
        starting_point = (request.form.get('starting_point') or '').strip()
        ending_point = (request.form.get('ending_point') or '').strip()
        start_date_raw = request.form.get('start_date')

        if not all([pass_type, price_raw, starting_point, ending_point, start_date_raw]):
            flash('Please fill all required pass details.', 'danger')
            return redirect(url_for('apply_pass'))

        try:
            start_date = datetime.strptime(start_date_raw, '%Y-%m-%d')
            duration_days = {
                'monthly': 30,
                'quarterly': 90,
                'yearly': 365
            }.get(pass_type, 30)
            end_date = start_date + timedelta(days=duration_days)
            price = float(price_raw)
        except ValueError:
            flash('Invalid date or price value.', 'danger')
            return redirect(url_for('apply_pass'))

        if not route:
            route = f'{starting_point} - {ending_point}'
        
        new_pass = BusPass(
            user_id=current_user.id,
            pass_type=pass_type,
            route=route,
            start_date=start_date,
            end_date=end_date,
            price=price,
            auto_renew=request.form.get('auto_renew') == 'on'
        )

        db.session.add(new_pass)
        db.session.commit()

        # Generate QR only after first commit so pass ID is available in QR payload.
        new_pass.generate_qr()
        db.session.commit()
        
        flash('Bus pass application submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('apply-pass.html')

@app.route('/renew-pass')
@login_required
def renew_pass_page():
    active_pass = BusPass.query.filter_by(user_id=current_user.id, status='active').first()
    return render_template('renew-pass.html', active_pass=active_pass)

@app.route('/renew-pass/<int:pass_id>', methods=['POST'])
@login_required
def renew_pass(pass_id):
    bus_pass = BusPass.query.get_or_404(pass_id)
    
    if bus_pass.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('dashboard'))
    
    bus_pass.end_date = bus_pass.end_date + timedelta(days=30)
    bus_pass.status = 'active'
    db.session.commit()
    
    flash('Pass renewed successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/qr-verification')
@login_required
def qr_verification():
    passes = BusPass.query.filter_by(user_id=current_user.id).all()
    qr_updated = False
    for bus_pass in passes:
        previous_qr = bus_pass.qr_code
        bus_pass.generate_qr()
        if bus_pass.qr_code != previous_qr:
            qr_updated = True

    if qr_updated:
        db.session.commit()

    return render_template('qr-verification.html', passes=passes)

@app.route('/verify-qr', methods=['POST'])
def verify_qr():
    data = request.json or {}
    qr_data = data.get('qr_data', '')

    qr_text = str(qr_data).strip()
    if not qr_text:
        return jsonify({'valid': False, 'message': 'QR data is empty'})

    # Enhanced QR format detection
    pass_match = re.search(r'PASS[:\s](\d+)', qr_text, re.IGNORECASE)
    if not pass_match:
        return jsonify({'valid': False, 'message': 'QR format is invalid'})

    pass_id = int(pass_match.group(1))
    bus_pass = BusPass.query.get(pass_id)
    if not bus_pass:
        return jsonify({'valid': False, 'message': f'Pass #{pass_id} not found'})

    if bus_pass.status != 'active':
        return jsonify({'valid': False, 'message': f'Pass status is {bus_pass.status}'})

    # Treat pass as valid for the whole expiry date (not only until midnight).
    today_utc = datetime.utcnow().date()
    if bus_pass.end_date.date() < today_utc:
        return jsonify({
            'valid': False,
            'message': f'Pass expired on {bus_pass.end_date.strftime("%Y-%m-%d")}'
        })

    # Log verification for analytics
    verification_log = {
        'timestamp': datetime.utcnow().isoformat(),
        'pass_id': pass_id,
        'user_id': bus_pass.user_id
    }

    route_parts = (bus_pass.route or '').split(' - ', 1)
    starting_point = route_parts[0] if route_parts else ''
    ending_point = route_parts[1] if len(route_parts) > 1 else ''

    return jsonify({
        'valid': True,
        'message': 'Valid pass',
        'user': bus_pass.user.full_name,
        'expiry': bus_pass.end_date.strftime('%Y-%m-%d'),
        'pass_type': bus_pass.pass_type,
        'route': bus_pass.route,
        'starting_point': starting_point,
        'ending_point': ending_point,
        'verification_id': hash(f"{pass_id}{datetime.utcnow().timestamp()}")
    })

@app.route('/trip-history')
@login_required
def trip_history():
    # Get filter parameters
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    search = request.args.get('search', '')
    
    # Base query
    query = Trip.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if month and year:
        query = query.filter(
            extract('month', Trip.timestamp) == month,
            extract('year', Trip.timestamp) == year
        )
    elif month:
        query = query.filter(extract('month', Trip.timestamp) == month)
    elif year:
        query = query.filter(extract('year', Trip.timestamp) == year)
    
    if search:
        query = query.filter(
            db.or_(
                Trip.route.ilike(f'%{search}%'),
                Trip.boarding_point.ilike(f'%{search}%'),
                Trip.drop_point.ilike(f'%{search}%')
            )
        )
    
    export_type = request.args.get('export', '').strip().lower()
    if export_type == 'csv':
        export_trips = query.order_by(desc(Trip.timestamp)).all()
        csv_lines = ['Date,Time,Route,From,To,Fare,Status']
        for trip in export_trips:
            date_str = trip.timestamp.strftime('%Y-%m-%d')
            time_str = trip.timestamp.strftime('%H:%M:%S')
            route = (trip.route or '').replace(',', ' ')
            boarding = (trip.boarding_point or '').replace(',', ' ')
            drop = (trip.drop_point or '').replace(',', ' ')
            fare = f'{trip.fare:.2f}' if trip.fare is not None else '0.00'
            status = (trip.status or 'completed').replace(',', ' ')
            csv_lines.append(f'{date_str},{time_str},{route},{boarding},{drop},{fare},{status}')

        csv_content = '\n'.join(csv_lines)
        filename = f'trip-history-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}.csv'
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )

    # Get paginated results
    page = request.args.get('page', 1, type=int)
    per_page = 10
    trips_pagination = query.order_by(desc(Trip.timestamp)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get statistics
    total_trips = Trip.query.filter_by(user_id=current_user.id).count()
    total_spent = db.session.query(db.func.sum(Trip.fare)).filter_by(user_id=current_user.id).scalar() or 0
    avg_fare = db.session.query(db.func.avg(Trip.fare)).filter_by(user_id=current_user.id).scalar() or 0
    active_pass_count = BusPass.query.filter_by(user_id=current_user.id, status='active').count()
    active_pass_total_amount = db.session.query(db.func.sum(BusPass.price)).filter_by(
        user_id=current_user.id, status='active'
    ).scalar() or 0

    pass_status_counts_raw = db.session.query(BusPass.status, db.func.count(BusPass.id)).filter_by(
        user_id=current_user.id
    ).group_by(BusPass.status).all()
    pass_status_counts = {'active': 0, 'expired': 0, 'cancelled': 0}
    for status, count in pass_status_counts_raw:
        pass_status_counts[status] = count
    
    # Get available years for filter
    years = db.session.query(
        extract('year', Trip.timestamp).label('year')
    ).filter_by(user_id=current_user.id).distinct().order_by('year').all()
    years = [int(y[0]) for y in years if y[0]]
    
    return render_template('trip-history.html', 
                         trips=trips_pagination.items,
                         pagination=trips_pagination,
                         total_trips=total_trips,
                         total_spent=total_spent,
                         avg_fare=round(avg_fare, 2),
                         active_pass_count=active_pass_count,
                         active_pass_total_amount=round(active_pass_total_amount, 2),
                         pass_status_counts=pass_status_counts,
                         years=years,
                         current_month=month,
                         current_year=year,
                         search=search)

@app.route('/api/trips/stats')
@login_required
def trip_stats():
    """API endpoint for trip statistics"""
    period = request.args.get('period', 'month')
    
    if period == 'week':
        start_date = datetime.utcnow() - timedelta(days=7)
        trips = Trip.query.filter(
            Trip.user_id == current_user.id,
            Trip.timestamp >= start_date
        ).all()
        
        # Group by day
        stats = {}
        fare_stats = {}
        for i in range(7):
            day = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
            stats[day] = 0
            fare_stats[day] = 0.0
        
        for trip in trips:
            day = trip.timestamp.strftime('%Y-%m-%d')
            if day in stats:
                stats[day] += 1
                fare_stats[day] += float(trip.fare or 0)
                
    elif period == 'month':
        start_date = datetime.utcnow() - timedelta(days=30)
        trips = Trip.query.filter(
            Trip.user_id == current_user.id,
            Trip.timestamp >= start_date
        ).all()
        
        # Group by week
        stats = {}
        fare_stats = {}
        for i in range(4):
            week_start = (datetime.utcnow() - timedelta(days=(i+1)*7)).strftime('Week %W')
            stats[week_start] = 0
            fare_stats[week_start] = 0.0
        
        for trip in trips:
            week = f"Week {trip.timestamp.strftime('%W')}"
            if week in stats:
                stats[week] += 1
                fare_stats[week] += float(trip.fare or 0)
    else:
        # Yearly stats
        current_year = datetime.utcnow().year
        trips = Trip.query.filter(
            Trip.user_id == current_user.id,
            extract('year', Trip.timestamp) == current_year
        ).all()
        
        # Group by month
        stats = {i: 0 for i in range(1, 13)}
        fare_stats = {i: 0.0 for i in range(1, 13)}
        for trip in trips:
            month = trip.timestamp.month
            stats[month] += 1
            fare_stats[month] += float(trip.fare or 0)

    labels = list(stats.keys())
    return jsonify({
        'labels': labels,
        'trip_counts': [stats[label] for label in labels],
        'fare_totals': [round(fare_stats[label], 2) for label in labels]
    })

@app.route('/add-trip', methods=['POST'])
@login_required
def add_trip():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['route', 'boarding', 'drop', 'fare']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        trip = Trip(
            user_id=current_user.id,
            route=data.get('route'),
            boarding_point=data.get('boarding'),
            drop_point=data.get('drop'),
            fare=float(data.get('fare'))
        )
        
        db.session.add(trip)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Trip recorded successfully',
            'trip_id': trip.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    if request.method == 'POST':
        try:
            # Create payment intent with Stripe
            amount = int(float(request.form.get('amount')) * 100)  # Convert to cents
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',
                metadata={'user_id': current_user.id}
            )
            
            payment = Payment(
                user_id=current_user.id,
                amount=float(request.form.get('amount')),
                payment_method='card',
                transaction_id=payment_intent.id,
                status='pending'
            )
            
            db.session.add(payment)
            db.session.commit()
            
            return jsonify({
                'clientSecret': payment_intent.client_secret,
                'payment_id': payment.id
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 403
    
    return render_template('payment.html', key=app.config['STRIPE_PUBLIC_KEY'])

@app.route('/payment-success/<int:payment_id>')
@login_required
def payment_success(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    payment.status = 'completed'
    db.session.commit()
    
    flash('Payment completed successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        address = (request.form.get('address') or '').strip()

        # Do not overwrite existing values with empty strings.
        if full_name:
            current_user.full_name = full_name
        if phone:
            current_user.phone = phone
        current_user.address = address
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

@app.route('/auto-renewal-toggle/<int:pass_id>', methods=['POST'])
@login_required
def toggle_auto_renewal(pass_id):
    bus_pass = BusPass.query.get_or_404(pass_id)
    
    if bus_pass.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    bus_pass.auto_renew = not bus_pass.auto_renew
    db.session.commit()
    
    return jsonify({
        'success': True,
        'auto_renew': bus_pass.auto_renew,
        'message': f'Auto-renewal {"enabled" if bus_pass.auto_renew else "disabled"}'
    })

@app.route('/api/translations/<lang>')
def get_translations(lang):
    translations = {
        'en': {
            'welcome': 'Welcome',
            'dashboard': 'Dashboard',
            'apply_pass': 'Apply for Pass',
            'renew_pass': 'Renew Pass',
            'trip_history': 'Trip History',
            'payment': 'Payment',
            'profile': 'Profile',
            'logout': 'Logout',
            'language': 'Language'
        },
        'es': {
            'welcome': 'Bienvenido',
            'dashboard': 'Panel',
            'apply_pass': 'Solicitar Pase',
            'renew_pass': 'Renovar Pase',
            'trip_history': 'Historial de Viajes',
            'payment': 'Pago',
            'profile': 'Perfil',
            'logout': 'Cerrar Sesión',
            'language': 'Idioma'
        },
        'fr': {
            'welcome': 'Bienvenue',
            'dashboard': 'Tableau de bord',
            'apply_pass': 'Demander un Pass',
            'renew_pass': 'Renouveler',
            'trip_history': 'Historique',
            'payment': 'Paiement',
            'profile': 'Profil',
            'logout': 'Déconnexion',
            'language': 'Langue'
        }
    }
    
    return jsonify(translations.get(lang, translations['en']))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
