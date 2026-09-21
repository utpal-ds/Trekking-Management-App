from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from functools import wraps
from models import db, User, Trek, Booking
from sqlalchemy import or_

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role='user').count()
    total_staff = User.query.filter_by(role='staff').count()
    total_bookings = Booking.query.count()
    
    # Recent bookings
    recent_bookings = Booking.query.order_by(Booking.booking_date.desc()).limit(5).all()
    
    return render_template(
        'admin_dashboard.html',
        active_page='admin_dashboard',
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings,
        recent_bookings=recent_bookings
    )

@admin_bp.route('/treks', methods=['GET', 'POST'])
@admin_required
def treks():
    staff_list = User.query.filter_by(role='staff', status='approved').all()
    
    if request.method == 'POST':
        # Add or Edit Trek
        trek_id = request.form.get('trek_id')
        name = request.form.get('name')
        location = request.form.get('location')
        difficulty = request.form.get('difficulty')
        duration = request.form.get('duration')
        available_slots = request.form.get('available_slots')
        assigned_staff_id = request.form.get('assigned_staff_id')
        status = request.form.get('status', 'Pending')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        description = request.form.get('description')
        
        # Validation
        if not name or not location or not difficulty or not duration or not available_slots or not start_date or not end_date:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('admin.treks'))
            
        try:
            duration = int(duration)
            available_slots = int(available_slots)
        except ValueError:
            flash('Duration and Slots must be integers.', 'danger')
            return redirect(url_for('admin.treks'))

        staff_id = int(assigned_staff_id) if assigned_staff_id else None
        
        if trek_id:
            # Edit
            trek = Trek.query.get(trek_id)
            if trek:
                trek.name = name
                trek.location = location
                trek.difficulty = difficulty
                trek.duration = duration
                
                # Adjust available slots if capacity changes
                diff = available_slots - trek.max_slots
                trek.max_slots = available_slots
                trek.available_slots = max(0, trek.available_slots + diff)
                
                trek.assigned_staff_id = staff_id
                trek.status = status
                trek.start_date = start_date
                trek.end_date = end_date
                trek.description = description
                flash('Trek updated successfully.', 'success')
        else:
            # Create
            new_trek = Trek(
                name=name,
                location=location,
                difficulty=difficulty,
                duration=duration,
                available_slots=available_slots,
                max_slots=available_slots,
                assigned_staff_id=staff_id,
                status=status,
                start_date=start_date,
                end_date=end_date,
                description=description
            )
            db.session.add(new_trek)
            flash('Trek created successfully.', 'success')
            
        db.session.commit()
        return redirect(url_for('admin.treks'))
        
    search_query = request.args.get('search', '')
    if search_query:
        trek_list = Trek.query.filter(
            or_(
                Trek.name.like(f'%{search_query}%'),
                Trek.location.like(f'%{search_query}%'),
                Trek.id == search_query
            )
        ).all()
    else:
        trek_list = Trek.query.all()
        
    return render_template(
        'admin_treks.html',
        active_page='admin_treks',
        trek_list=trek_list,
        staff_list=staff_list,
        search_query=search_query
    )

@admin_bp.route('/treks/delete/<int:trek_id>', methods=['POST'])
@admin_required
def delete_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    # Check if there are active bookings
    active_bookings = Booking.query.filter_by(trek_id=trek_id, status='Booked').count()
    if active_bookings > 0:
        flash('Cannot delete trek with active bookings.', 'danger')
    else:
        db.session.delete(trek)
        db.session.commit()
        flash('Trek deleted successfully.', 'success')
    return redirect(url_for('admin.treks'))

@admin_bp.route('/staff')
@admin_required
def staff():
    pending_staff = User.query.filter_by(role='staff', status='pending').all()
    approved_staff = User.query.filter_by(role='staff', status='approved').all()
    blacklisted_staff = User.query.filter_by(role='staff', status='blacklisted').all()
    
    return render_template(
        'admin_staff.html',
        active_page='admin_staff',
        pending_staff=pending_staff,
        approved_staff=approved_staff,
        blacklisted_staff=blacklisted_staff
    )

@admin_bp.route('/staff/action/<int:staff_id>/<string:action_type>', methods=['POST'])
@admin_required
def staff_action(staff_id, action_type):
    staff_user = User.query.get_or_404(staff_id)
    if staff_user.role != 'staff':
        flash('User is not a staff member.', 'danger')
        return redirect(url_for('admin.staff'))
        
    if action_type == 'approve':
        staff_user.status = 'approved'
        flash(f'Staff {staff_user.name} approved successfully.', 'success')
    elif action_type == 'blacklist':
        staff_user.status = 'blacklisted'
        # Unassign from treks
        for trek in staff_user.assigned_treks:
            trek.assigned_staff_id = None
        flash(f'Staff {staff_user.name} blacklisted and unassigned from all treks.', 'warning')
    elif action_type == 'reject':
        db.session.delete(staff_user)
        flash(f'Staff registration request rejected.', 'info')
        
    db.session.commit()
    return redirect(url_for('admin.staff'))

@admin_bp.route('/users')
@admin_required
def users():
    users_list = User.query.filter_by(role='user').all()
    return render_template(
        'admin_users.html',
        active_page='admin_users',
        users_list=users_list
    )

@admin_bp.route('/users/blacklist/<int:user_id>', methods=['POST'])
@admin_required
def blacklist_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot blacklist admin.', 'danger')
        return redirect(url_for('admin.users'))
        
    if user.status == 'blacklisted':
        user.status = 'approved'
        flash(f'User {user.name} un-blacklisted.', 'success')
    else:
        user.status = 'blacklisted'
        # Cancel all active bookings
        bookings = Booking.query.filter_by(user_id=user_id, status='Booked').all()
        for booking in bookings:
            booking.status = 'Cancelled'
            # Restore slots
            trek = Trek.query.get(booking.trek_id)
            if trek:
                trek.available_slots += booking.slots_booked
        flash(f'User {user.name} blacklisted. All their active bookings have been cancelled.', 'warning')
        
    db.session.commit()
    return redirect(url_for('admin.users'))

@admin_bp.route('/bookings')
@admin_required
def bookings():
    bookings_list = Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template(
        'admin_bookings.html',
        active_page='admin_bookings',
        bookings_list=bookings_list
    )

@admin_bp.route('/search')
@admin_required
def search():
    query = request.args.get('q', '')
    treks_results = []
    staff_results = []
    users_results = []
    
    if query:
        # Search treks
        treks_results = Trek.query.filter(
            or_(
                Trek.name.like(f'%{query}%'),
                Trek.location.like(f'%{query}%'),
                Trek.id == query
            )
        ).all()
        
        # Search staff
        staff_results = User.query.filter(
            User.role == 'staff',
            or_(
                User.name.like(f'%{query}%'),
                User.username.like(f'%{query}%'),
                User.id == query
            )
        ).all()
        
        # Search users
        users_results = User.query.filter(
            User.role == 'user',
            or_(
                User.name.like(f'%{query}%'),
                User.username.like(f'%{query}%'),
                User.id == query
            )
        ).all()
        
    return render_template(
        'admin_search.html',
        active_page='admin_search',
        query=query,
        treks_results=treks_results,
        staff_results=staff_results,
        users_results=users_results
    )

@admin_bp.route('/reports')
@admin_required
def reports():
    # Gather analytics
    total_bookings = Booking.query.count()
    active_bookings = Booking.query.filter_by(status='Booked').count()
    completed_bookings = Booking.query.filter_by(status='Completed').count()
    cancelled_bookings = Booking.query.filter_by(status='Cancelled').count()
    
    difficulty_stats = db.session.query(Trek.difficulty, db.func.count(Trek.id)).group_by(Trek.difficulty).all()
    difficulty_map = {diff: count for diff, count in difficulty_stats}
    
    most_popular_treks = db.session.query(
        Trek.name, db.func.sum(Booking.slots_booked)
    ).join(Booking).filter(Booking.status == 'Booked').group_by(Trek.name).order_by(db.func.sum(Booking.slots_booked).desc()).limit(5).all()
    
    return render_template(
        'admin_reports.html',
        active_page='admin_reports',
        total_bookings=total_bookings,
        active_bookings=active_bookings,
        completed_bookings=completed_bookings,
        cancelled_bookings=cancelled_bookings,
        difficulty_map=difficulty_map,
        most_popular_treks=most_popular_treks
    )
