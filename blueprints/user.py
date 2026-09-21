from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from functools import wraps
from models import db, User, Trek, Booking
from datetime import datetime

user_bp = Blueprint('user', __name__, url_prefix='/user')

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'user':
            flash('Access denied. Trekker account required.', 'danger')
            return redirect(url_for('auth.login'))
            
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user or user.status == 'blacklisted':
            flash('Your account has been blacklisted. Access denied.', 'danger')
            session.clear()
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function

@user_bp.route('/dashboard')
@user_required
def dashboard():
    user_id = session.get('user_id')
    
    # Available treks filter parameters
    difficulty = request.args.get('difficulty', 'All')
    location = request.args.get('location', 'All')
    
    # Fetch list of distinct locations for the filter dropdown
    locations = [t.location for t in db.session.query(Trek.location).distinct().all()]
    
    # Base query for treks that are Open (Status 'Open') and have slots
    query = Trek.query.filter(Trek.status == 'Open', Trek.available_slots > 0)
    
    if difficulty != 'All':
        query = query.filter(Trek.difficulty == difficulty)
    if location != 'All':
        query = query.filter(Trek.location == location)
        
    available_treks = query.all()
    
    # Active bookings summary for this user
    active_bookings = Booking.query.filter_by(user_id=user_id, status='Booked').order_by(Booking.booking_date.desc()).limit(3).all()
    
    return render_template(
        'user_dashboard.html',
        active_page='user_dashboard',
        available_treks=available_treks,
        active_bookings=active_bookings,
        locations=locations,
        selected_difficulty=difficulty,
        selected_location=location
    )

@user_bp.route('/browse')
@user_required
def browse_treks():
    return redirect(url_for('user.dashboard'))

@user_bp.route('/trek/<int:trek_id>')
@user_required
def trek_detail(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    return render_template('user_trek_detail.html', active_page='user_dashboard', trek=trek)

@user_bp.route('/book/<int:trek_id>', methods=['POST'])
@user_required
def book_trek(trek_id):
    user_id = session.get('user_id')
    trek = Trek.query.get_or_404(trek_id)
    
    # Check if trek is Open
    if trek.status != 'Open':
        flash('This trek is currently not open for bookings.', 'danger')
        return redirect(url_for('user.trek_detail', trek_id=trek.id))
        
    # Check slot availability
    slots = request.form.get('slots', 1)
    try:
        slots = int(slots)
    except ValueError:
        slots = 1
        
    if slots < 1:
        flash('Please select at least 1 slot.', 'danger')
        return redirect(url_for('user.trek_detail', trek_id=trek.id))
        
    if trek.available_slots < slots:
        flash(f'Sorry! Only {trek.available_slots} slots are available.', 'danger')
        return redirect(url_for('user.trek_detail', trek_id=trek.id))
        
    # Prevent booking duplicate active bookings for the same trek
    existing_booking = Booking.query.filter_by(user_id=user_id, trek_id=trek_id, status='Booked').first()
    if existing_booking:
        flash('You already have an active booking for this trek.', 'warning')
        return redirect(url_for('user.my_bookings'))
        
    # Book the trek
    booking = Booking(
        user_id=user_id,
        trek_id=trek.id,
        slots_booked=slots,
        status='Booked',
        booking_date=datetime.utcnow()
    )
    
    # Decrement slots
    trek.available_slots -= slots
    
    db.session.add(booking)
    db.session.commit()
    
    flash(f'Trek booking for "{trek.name}" confirmed successfully!', 'success')
    return redirect(url_for('user.my_bookings'))

@user_bp.route('/bookings')
@user_required
def my_bookings():
    user_id = session.get('user_id')
    # Filter bookings that are Booked
    bookings = Booking.query.filter_by(user_id=user_id, status='Booked').order_by(Booking.booking_date.desc()).all()
    return render_template('user_bookings.html', active_page='user_bookings', bookings=bookings)

@user_bp.route('/bookings/cancel/<int:booking_id>', methods=['POST'])
@user_required
def cancel_booking(booking_id):
    user_id = session.get('user_id')
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != user_id:
        flash('Unauthorized booking access.', 'danger')
        return redirect(url_for('user.my_bookings'))
        
    if booking.status != 'Booked':
        flash('Only active bookings can be cancelled.', 'danger')
        return redirect(url_for('user.my_bookings'))
        
    # Cancel booking
    booking.status = 'Cancelled'
    
    # Restore slots
    trek = Trek.query.get(booking.trek_id)
    if trek:
        trek.available_slots += booking.slots_booked
        
    db.session.commit()
    flash('Booking cancelled successfully.', 'warning')
    return redirect(url_for('user.my_bookings'))

@user_bp.route('/history')
@user_required
def history():
    user_id = session.get('user_id')
    # Completed or Cancelled bookings
    bookings = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.status.in_(['Completed', 'Cancelled'])
    ).order_by(Booking.booking_date.desc()).all()
    
    return render_template('user_history.html', active_page='user_history', bookings=bookings)

@user_bp.route('/profile', methods=['GET', 'POST'])
@user_required
def profile():
    user_id = session.get('user_id')
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        contact_details = request.form.get('contact_details')
        
        if not name:
            flash('Name is required.', 'danger')
            return redirect(url_for('user.profile'))
            
        user.name = name
        user.contact_details = contact_details
        db.session.commit()
        
        session['name'] = name
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('user.profile'))
        
    return render_template('user_profile.html', active_page='user_profile', user=user)
