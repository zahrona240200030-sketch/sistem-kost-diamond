import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kost123456789'

# Database configuration for Vercel
if 'VERCEL' in os.environ:
    # Production (Vercel)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/identitas_kost.db'
else:
    # Development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///identitas_kost.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model Database - FINAL SCHEMA
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')

class Mahasiswa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nim = db.Column(db.String(20), unique=True, nullable=False)
    nama = db.Column(db.String(100), nullable=False)
    asal = db.Column(db.Text, nullable=False)
    jurusan = db.Column(db.String(50), nullable=False)
    no_hp = db.Column(db.String(15), nullable=False)
    no_hp_ortu = db.Column(db.String(15), nullable=False)
    kamar = db.Column(db.String(10), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class StatusLangganan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mahasiswa_id = db.Column(db.Integer, db.ForeignKey('mahasiswa.id'), nullable=False)
    bulan = db.Column(db.String(7), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    tanggal_update = db.Column(db.DateTime, default=datetime.utcnow)
    mahasiswa = db.relationship('Mahasiswa', backref='status_langganan')

class Keluhan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_pengeluh = db.Column(db.String(100), nullable=False)
    kamar = db.Column(db.String(10))
    isi_keluhan = db.Column(db.Text, nullable=False)
    foto_keluhan = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')
    tanggal_keluhan = db.Column(db.DateTime, default=datetime.utcnow)

# Decorator untuk login required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ===== ROUTES UTAMA =====
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah!', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Password tidak cocok!', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan!', 'danger')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    total_mahasiswa = Mahasiswa.query.count()
    mahasiswa_list = Mahasiswa.query.limit(5).all()
    return render_template('dashboard.html', 
                         total_mahasiswa=total_mahasiswa,
                         mahasiswa_list=mahasiswa_list)

@app.route('/mahasiswa')
@login_required
def mahasiswa():
    search = request.args.get('search', '')
    if search:
        mahasiswa_list = Mahasiswa.query.filter(
            (Mahasiswa.nama.contains(search)) | 
            (Mahasiswa.nim.contains(search)) |
            (Mahasiswa.jurusan.contains(search))
        ).order_by(Mahasiswa.nama).all()
    else:
        mahasiswa_list = Mahasiswa.query.order_by(Mahasiswa.nama).all()
    
    return render_template('mahasiswa.html', mahasiswa_list=mahasiswa_list, search=search)

@app.route('/mahasiswa/tambah', methods=['GET', 'POST'])
@login_required
def tambah_mahasiswa():
    if request.method == 'POST':
        nim = request.form['nim']
        nama = request.form['nama']
        asal = request.form['asal']
        jurusan = request.form['jurusan']
        no_hp = request.form['no_hp']
        no_hp_ortu = request.form['no_hp_ortu']
        kamar = request.form['kamar']
        
        if Mahasiswa.query.filter_by(nim=nim).first():
            flash('NIM sudah terdaftar!', 'danger')
            return render_template('tambah_mahasiswa.html')
        
        new_mahasiswa = Mahasiswa(
            nim=nim,
            nama=nama,
            asal=asal,
            jurusan=jurusan,
            no_hp=no_hp,
            no_hp_ortu=no_hp_ortu,
            kamar=kamar,
            created_by=session['user_id']
        )
        
        db.session.add(new_mahasiswa)
        db.session.commit()
        
        flash('Data mahasiswa berhasil ditambahkan!', 'success')
        return redirect(url_for('mahasiswa'))
    
    return render_template('tambah_mahasiswa.html')

@app.route('/mahasiswa/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_mahasiswa(id):
    mahasiswa = Mahasiswa.query.get_or_404(id)
    
    if request.method == 'POST':
        mahasiswa.nama = request.form['nama']
        mahasiswa.asal = request.form['asal']
        mahasiswa.jurusan = request.form['jurusan']
        mahasiswa.no_hp = request.form['no_hp']
        mahasiswa.no_hp_ortu = request.form['no_hp_ortu']
        mahasiswa.kamar = request.form['kamar']
        
        db.session.commit()
        flash('Data mahasiswa berhasil diupdate!', 'success')
        return redirect(url_for('mahasiswa'))
    
    return render_template('edit_mahasiswa.html', mahasiswa=mahasiswa)

@app.route('/mahasiswa/hapus/<int:id>')
@login_required
def hapus_mahasiswa(id):
    mahasiswa = Mahasiswa.query.get_or_404(id)
    db.session.delete(mahasiswa)
    db.session.commit()
    flash('Data mahasiswa berhasil dihapus!', 'success')
    return redirect(url_for('mahasiswa'))

# ===== ROUTES FITUR BARU =====
@app.route('/status', methods=['GET', 'POST'])
def status_langganan():
    """Halaman update status langganan"""
    bulan_sekarang = datetime.now().strftime('%Y-%m')
    
    if request.method == 'POST':
        nim = request.form['nim']
        status = request.form['status']
        
        mahasiswa = Mahasiswa.query.filter_by(nim=nim).first()
        
        if not mahasiswa:
            flash('NIM tidak ditemukan!', 'danger')
            return render_template('status_langganan.html', bulan_sekarang=bulan_sekarang)
        
        existing_status = StatusLangganan.query.filter_by(
            mahasiswa_id=mahasiswa.id, 
            bulan=bulan_sekarang
        ).first()
        
        if existing_status:
            existing_status.status = status
        else:
            new_status = StatusLangganan(
                mahasiswa_id=mahasiswa.id,
                bulan=bulan_sekarang,
                status=status
            )
            db.session.add(new_status)
        
        db.session.commit()
        flash(f'Status berhasil diupdate! {mahasiswa.nama} - {status.upper()}', 'success')
        return redirect(url_for('status_langganan'))
    
    return render_template('status_langganan.html', bulan_sekarang=bulan_sekarang)

@app.route('/status-kost')
def status_kost():
    """Halaman lihat status semua penghuni"""
    bulan_sekarang = datetime.now().strftime('%Y-%m')
    
    status_list = StatusLangganan.query.filter_by(bulan=bulan_sekarang)\
        .join(Mahasiswa)\
        .add_columns(Mahasiswa.nama, Mahasiswa.kamar, StatusLangganan.status)\
        .all()
    
    return render_template('status_kost.html', 
                         status_list=status_list, 
                         bulan_sekarang=bulan_sekarang)

@app.route('/keluhan', methods=['GET', 'POST'])
def keluhan():
    """Halaman untuk mengirim keluhan"""
    if request.method == 'POST':
        nama = request.form['nama']
        kamar = request.form['kamar']
        isi_keluhan = request.form['keluhan']
        foto = request.files.get('foto')
        
        foto_filename = None
        if foto and foto.filename != '':
            ext = foto.filename.split('.')[-1]
            foto_filename = f"{uuid.uuid4().hex}.{ext}"
            os.makedirs('static/uploads', exist_ok=True)
            foto.save(f'static/uploads/{foto_filename}')
        
        new_keluhan = Keluhan(
            nama_pengeluh=nama,
            kamar=kamar,
            isi_keluhan=isi_keluhan,
            foto_keluhan=foto_filename
        )
        
        db.session.add(new_keluhan)
        db.session.commit()
        
        flash('Keluhan berhasil dikirim! Terima kasih atas feedbacknya.', 'success')
        return redirect(url_for('keluhan'))
    
    return render_template('keluhan.html')

@app.route('/admin/keluhan')
@login_required
def admin_keluhan():
    keluhan_list = Keluhan.query.order_by(Keluhan.tanggal_keluhan.desc()).all()
    return render_template('admin_keluhan.html', keluhan_list=keluhan_list)

@app.route('/admin/keluhan/update/<int:id>', methods=['POST'])
@login_required
def update_status_keluhan(id):
    keluhan = Keluhan.query.get_or_404(id)
    keluhan.status = request.form['status']
    db.session.commit()
    flash('Status keluhan berhasil diupdate!', 'success')
    return redirect(url_for('admin_keluhan'))

@app.route('/admin/status-langganan')
@login_required
def admin_status_langganan():
    mahasiswa_list = Mahasiswa.query.all()
    bulan_sekarang = datetime.now().strftime('%Y-%m')
    
    return render_template('admin_status_langganan.html', 
                         mahasiswa_list=mahasiswa_list,
                         bulan_sekarang=bulan_sekarang)

@app.route('/admin/update-status', methods=['POST'])
@login_required
def update_status_langganan():
    mahasiswa_id = request.form['mahasiswa_id']
    bulan = request.form['bulan']
    status = request.form['status']
    
    existing_status = StatusLangganan.query.filter_by(
        mahasiswa_id=mahasiswa_id, 
        bulan=bulan
    ).first()
    
    if existing_status:
        existing_status.status = status
    else:
        new_status = StatusLangganan(
            mahasiswa_id=mahasiswa_id,
            bulan=bulan,
            status=status
        )
        db.session.add(new_status)
    
    db.session.commit()
    flash('Status langganan berhasil diupdate!', 'success')
    return redirect(url_for('admin_status_langganan'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout berhasil!', 'success')
    return redirect(url_for('index'))

# Test route untuk cek database
@app.route('/test-db')
def test_db():
    try:
        count = Mahasiswa.query.count()
        return f"✅ Database OK! Total mahasiswa: {count}"
    except Exception as e:
        return f"❌ Database ERROR: {str(e)}"

# Buat database dengan FORCE RESET
def init_db():
    with app.app_context():
        try:
            print("🔄 Force reset database...")
            db.drop_all()
            print("✅ Tables dropped")
            
            db.create_all()
            print("✅ New tables created")
            
            # Buat admin user
            # Buat admin user jika belum ada
        if not User.query.filter_by(username='admin').first():
            admin_password = generate_password_hash('admin123')
            admin_user = User(username='admin', password=admin_password, role='admin')
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Admin user created: username=admin, password=admin123")
        else:
            # Reset password admin yang sudah ada
            admin = User.query.filter_by(username='admin').first()
            admin.password = generate_password_hash('admin123')
            db.session.commit()
            print("✅ Admin password reset: admin / admin123")
            
            # Test schema
            columns = db.session.execute(db.text("PRAGMA table_info(mahasiswa)")).fetchall()
            column_names = [col[1] for col in columns]
            print(f"✅ Mahasiswa table columns: {column_names}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import sqlite3
            if os.path.exists('identitas_kost.db'):
                os.remove('identitas_kost.db')
            db.create_all()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
else:
    # Untuk production (Vercel)
    with app.app_context():

        db.create_all()
