from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
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

@app.route('/dashboard')
@login_required
def dashboard():
    active_pass = BusPass.query.filter_by(user_id=current_user.id, status='active').first()
    if active_pass:
        previous_qr = active_pass.qr_code
        active_pass.generate_qr()
        if active_pass.qr_code != previous_qr:
            db.session.commit()
    recent_trips = Trip.query.filter_by(user_id=current_user.id).order_by(Trip.timestamp.desc()).limit(5).all()
    return render_template('dashboard.html', active_pass=active_pass, recent_trips=recent_trips)

@app.route('/apply-pass', methods=['GET', 'POST'])
@login_required
def apply_pass():
    if request.method == 'POST':
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = start_date + timedelta(days=30)  # Default monthly pass
        
        new_pass = BusPass(
            user_id=current_user.id,
            pass_type=request.form.get('pass_type'),
            route=request.form.get('route'),
            start_date=start_date,
            end_date=end_date,
            price=float(request.form.get('price')),
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

    return jsonify({
        'valid': True,
        'message': 'Valid pass',
        'user': bus_pass.user.full_name,
        'expiry': bus_pass.end_date.strftime('%Y-%m-%d'),
        'pass_type': bus_pass.pass_type,
        'route': bus_pass.route,
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
        for i in range(7):
            day = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
            stats[day] = 0
        
        for trip in trips:
            day = trip.timestamp.strftime('%Y-%m-%d')
            if day in stats:
                stats[day] += 1
                
    elif period == 'month':
        start_date = datetime.utcnow() - timedelta(days=30)
        trips = Trip.query.filter(
            Trip.user_id == current_user.id,
            Trip.timestamp >= start_date
        ).all()
        
        # Group by week
        stats = {}
        for i in range(4):
            week_start = (datetime.utcnow() - timedelta(days=(i+1)*7)).strftime('Week %W')
            stats[week_start] = 0
        
        for trip in trips:
            week = f"Week {trip.timestamp.strftime('%W')}"
            if week in stats:
                stats[week] += 1
    else:
        # Yearly stats
        current_year = datetime.utcnow().year
        trips = Trip.query.filter(
            Trip.user_id == current_user.id,
            extract('year', Trip.timestamp) == current_year
        ).all()
        
        # Group by month
        stats = {i: 0 for i in range(1, 13)}
        for trip in trips:
            month = trip.timestamp.month
            stats[month] += 1
    
    return jsonify(stats)

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