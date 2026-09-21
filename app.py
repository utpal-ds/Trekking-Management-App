
from flask import Flask, redirect, url_for, session
from models import db, User, Trek
from werkzeug.security import generate_password_hash

# Import Blueprints
from blueprints.auth import auth_bp
from blueprints.admin import admin_bp
from blueprints.staff import staff_bp
from blueprints.user import user_bp
from blueprints.api import api_bp



def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev_key_for_trekking_app_12938123'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trekking.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize db
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(api_bp)
    
    @app.route('/')
    def index():
        role = session.get('role')
        if not role:
            return redirect(url_for('auth.login'))
            
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'staff':
            return redirect(url_for('staff.dashboard'))
        else:
            return redirect(url_for('user.dashboard'))
            
    # Programmatic database setup and seeding
    with app.app_context():
        db.create_all()
        
        # Seed default Admin account if not present
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                name='Admin Superuser',
                contact_details='admin@trekmanage.com',
                role='admin',
                password_hash=generate_password_hash('admin123'),
                status='approved'
            )
            db.session.add(admin_user)
            db.session.commit()
            
        # Seed some initial mock treks if database is completely empty of treks
        if Trek.query.count() == 0:
            mock_treks = [
                Trek(
                    name='Everest Base Camp',
                    location='Nepal',
                    difficulty='Hard',
                    duration=12,
                    available_slots=20,
                    max_slots=20,
                    status='Open',
                    start_date='2026-09-10',
                    end_date='2026-09-22',
                    description='A legendary trek in Nepal offering spectacular close-up views of Mount Everest, Ama Dablam, and other massive peaks.'
                ),
                Trek(
                    name='Roopkund Trek',
                    location='Uttarakhand',
                    difficulty='Moderate',
                    duration=7,
                    available_slots=15,
                    max_slots=15,
                    status='Open',
                    start_date='2026-10-05',
                    end_date='2026-10-12',
                    description='Famous for its mysterious skeletal lake, the Roopkund trek winds through lush meadows (bugyals) and steep snow patches.'
                ),
                Trek(
                    name='Kedarkantha Trek',
                    location='Uttarakhand',
                    difficulty='Easy',
                    duration=6,
                    available_slots=20,
                    max_slots=20,
                    status='Closed',
                    start_date='2026-12-20',
                    end_date='2026-12-26',
                    description='A classic winter summit trek in the Himalayas. The path features stunning snow forests and a majestic 360-degree peak view.'
                ),
                Trek(
                    name='Hampta Pass',
                    location='Himachal',
                    difficulty='Moderate',
                    duration=5,
                    available_slots=12,
                    max_slots=12,
                    status='Open',
                    start_date='2026-08-15',
                    end_date='2026-08-20',
                    description='A dramatic pass crossing from the green Kullu valley to the arid, high-altitude desert of Spiti, Himachal Pradesh.'
                )
            ]
            for trek in mock_treks:
                db.session.add(trek)
            db.session.commit()
            
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
