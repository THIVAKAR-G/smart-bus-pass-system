from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import qrcode
import io
import base64

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200))
    user_type = db.Column(db.String(20), nullable=False)  # student, professional, senior
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    passes = db.relationship('BusPass', backref='user', lazy=True)
    trips = db.relationship('Trip', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)

class BusPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pass_type = db.Column(db.String(50), nullable=False)  # monthly, quarterly, yearly
    route = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, expired, cancelled
    qr_code = db.Column(db.Text)
    auto_renew = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def generate_qr(self):
        qr_data = f"PASS:{self.id}:USER:{self.user_id}:VALID:{self.end_date}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        self.qr_code = base64.b64encode(buffered.getvalue()).decode()

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pass_id = db.Column(db.Integer, db.ForeignKey('bus_pass.id'))
    route = db.Column(db.String(200), nullable=False)
    boarding_point = db.Column(db.String(100))
    drop_point = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    fare = db.Column(db.Float)
    status = db.Column(db.String(20), default='completed')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pass_id = db.Column(db.Integer, db.ForeignKey('bus_pass.id'))
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default='completed')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
