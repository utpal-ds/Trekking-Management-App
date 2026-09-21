from flask import Blueprint, jsonify, session
from models import db, User, Trek, Booking

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/treks', methods=['GET'])
def get_treks():
    # Public API to fetch open treks
    treks = Trek.query.filter_by(status='Open').all()
    output = []
    for t in treks:
        output.append({
            'id': t.id,
            'name': t.name,
            'location': t.location,
            'difficulty': t.difficulty,
            'duration_days': t.duration,
            'available_slots': t.available_slots,
            'max_slots': t.max_slots,
            'start_date': t.start_date,
            'end_date': t.end_date
        })
    return jsonify({'treks': output})

@api_bp.route('/users', methods=['GET'])
def get_users():
    # Restrict to Admin
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403
        
    users = User.query.filter_by(role='user').all()
    output = []
    for u in users:
        output.append({
            'id': u.id,
            'username': u.username,
            'name': u.name,
            'contact_details': u.contact_details,
            'status': u.status
        })
    return jsonify({'users': output})

@api_bp.route('/bookings', methods=['GET'])
def get_bookings():
    # Restrict to Admin and Staff
    if session.get('role') not in ['admin', 'staff']:
        return jsonify({'error': 'Unauthorized access'}), 403
        
    bookings = Booking.query.all()
    output = []
    for b in bookings:
        output.append({
            'id': b.id,
            'user_id': b.user_id,
            'user_name': b.user.name,
            'trek_id': b.trek_id,
            'trek_name': b.trek.name,
            'slots_booked': b.slots_booked,
            'booking_date': b.booking_date.isoformat(),
            'status': b.status
        })
    return jsonify({'bookings': output})
