from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from functools import wraps
from models import db, User, Trek, Booking

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'staff':
            flash('Access denied. Staff privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check staff approval status
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user or user.status != 'approved':
            flash('Your account status does not permit dashboard access.', 'danger')
            session.clear()
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function

@staff_bp.route('/dashboard')
@staff_required
def dashboard():
    staff_id = session.get('user_id')
    assigned_treks = Trek.query.filter_by(assigned_staff_id=staff_id).all()
    
    # Calculate metrics
    num_assigned = len(assigned_treks)
    num_open = sum(1 for t in assigned_treks if t.status == 'Open')
    
    # Total participants across all assigned treks
    total_participants = 0
    for trek in assigned_treks:
        total_participants += sum(b.slots_booked for b in trek.bookings if b.status == 'Booked')
        
    return render_template(
        'staff_dashboard.html',
        active_page='staff_dashboard',
        assigned_treks=assigned_treks,
        num_assigned=num_assigned,
        num_open=num_open,
        total_participants=total_participants
    )

@staff_bp.route('/my-treks')
@staff_required
def my_treks():
    staff_id = session.get('user_id')
    assigned_treks = Trek.query.filter_by(assigned_staff_id=staff_id).all()
    return render_template(
        'staff_dashboard.html',
        active_page='staff_treks',
        assigned_treks=assigned_treks
    )

@staff_bp.route('/trek/<int:trek_id>', methods=['GET', 'POST'])
@staff_required
def manage_trek(trek_id):
    staff_id = session.get('user_id')
    trek = Trek.query.get_or_404(trek_id)
    
    # Check permissions
    if trek.assigned_staff_id != staff_id:
        flash('Unauthorized. You are not assigned to this trek.', 'danger')
        return redirect(url_for('staff.dashboard'))
        
    if request.method == 'POST':
        # Update slots and status
        status = request.form.get('status')
        available_slots = request.form.get('available_slots')
        
        if status:
            trek.status = status
            
            # If marked completed, also mark bookings completed
            if status == 'Completed':
                for booking in trek.bookings:
                    if booking.status == 'Booked':
                        booking.status = 'Completed'
            
        if available_slots:
            try:
                slots = int(available_slots)
                # Available slots cannot exceed max slots (original capacity)
                if slots > trek.max_slots:
                    flash(f'Slots cannot exceed original capacity of {trek.max_slots}.', 'danger')
                else:
                    trek.available_slots = slots
            except ValueError:
                flash('Slots must be a number.', 'danger')
                
        db.session.commit()
        flash('Trek updated successfully.', 'success')
        return redirect(url_for('staff.manage_trek', trek_id=trek.id))
        
    # Get active bookings (participants)
    bookings = Booking.query.filter_by(trek_id=trek.id, status='Booked').all()
    
    return render_template(
        'staff_trek_detail.html',
        active_page='staff_dashboard',
        trek=trek,
        bookings=bookings
    )

@staff_bp.route('/trek/<int:trek_id>/action/<string:action_type>', methods=['POST'])
@staff_required
def trek_action(trek_id, action_type):
    staff_id = session.get('user_id')
    trek = Trek.query.get_or_404(trek_id)
    
    if trek.assigned_staff_id != staff_id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('staff.dashboard'))
        
    if action_type == 'start':
        trek.status = 'Open'
        flash('Trek status updated to Open (Started).', 'success')
    elif action_type == 'complete':
        trek.status = 'Completed'
        # Mark all active bookings completed
        for booking in trek.bookings:
            if booking.status == 'Booked':
                booking.status = 'Completed'
        flash('Trek marked as Completed.', 'success')
        
    db.session.commit()
    return redirect(url_for('staff.manage_trek', trek_id=trek.id))

@staff_bp.route('/participants')
@staff_required
def participants():
    staff_id = session.get('user_id')
    assigned_treks = Trek.query.filter_by(assigned_staff_id=staff_id).all()
    trek_ids = [t.id for t in assigned_treks]
    
    # List of all active bookings for this staff's assigned treks
    bookings = Booking.query.filter(Booking.trek_id.in_(trek_ids), Booking.status == 'Booked').all()
    
    return render_template(
        'staff_participants.html',
        active_page='staff_participants',
        bookings=bookings
    )

@staff_bp.route('/profile', methods=['GET', 'POST'])
@staff_required
def profile():
    user_id = session.get('user_id')
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        contact_details = request.form.get('contact_details')
        
        if not name:
            flash('Name is required.', 'danger')
            return redirect(url_for('staff.profile'))
            
        user.name = name
        user.contact_details = contact_details
        db.session.commit()
        
        session['name'] = name
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('staff.profile'))
        
    return render_template(
        'staff_profile.html',
        active_page='staff_profile',
        user=user
    )
