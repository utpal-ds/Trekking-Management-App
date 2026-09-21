from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    contact_details = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'staff', 'user'
    status = db.Column(db.String(20), nullable=False, default='approved') # 'pending', 'approved', 'blacklisted'
    
    # Relationships
    assigned_treks = db.relationship('Trek', backref='assigned_staff', lazy=True)
    bookings = db.relationship('Booking', backref='user', lazy=True)

    def is_approved_staff(self):
        return self.role == 'staff' and self.status == 'approved'

    def is_blacklisted(self):
        return self.status == 'blacklisted'

class Trek(db.Model):
    __tablename__ = 'treks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False) # 'Easy', 'Moderate', 'Hard'
    duration = db.Column(db.Integer, nullable=False) # in days
    available_slots = db.Column(db.Integer, nullable=False)
    max_slots = db.Column(db.Integer, nullable=False)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Pending') # 'Pending', 'Approved', 'Open', 'Closed', 'Completed'
    start_date = db.Column(db.String(20), nullable=False) # 'YYYY-MM-DD'
    end_date = db.Column(db.String(20), nullable=False) # 'YYYY-MM-DD'
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    bookings = db.relationship('Booking', backref='trek', lazy=True)

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey('treks.id'), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    slots_booked = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default='Booked') # 'Booked', 'Cancelled', 'Completed'
