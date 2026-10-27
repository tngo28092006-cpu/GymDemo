import os, sqlite3, calendar, secrets, smtplib, re
from datetime import date, datetime
from pathlib import Path
from functools import wraps
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config['DATABASE'] = str(Path(__file__).with_name('gym.db'))
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')

def db():
    c = sqlite3.connect(app.config['DATABASE'])
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def init_db():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT);
        CREATE TABLE IF NOT EXISTS packages(id INTEGER PRIMARY KEY, months INTEGER UNIQUE, price INTEGER CHECK(price>0));
        CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY, name TEXT, gender TEXT, birth INTEGER, phone TEXT, email TEXT, registered TEXT, source TEXT, trainer INTEGER REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY, member INTEGER REFERENCES members(id), months INTEGER, amount INTEGER, created TEXT, paid_at TEXT, starts TEXT, expires TEXT);
        CREATE TABLE IF NOT EXISTS exercises(id INTEGER PRIMARY KEY, name TEXT UNIQUE, active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS plans(id INTEGER PRIMARY KEY, member INTEGER REFERENCES members(id), exercise INTEGER REFERENCES exercises(id), sets INTEGER, reps INTEGER, days TEXT);
        CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1), max_days INTEGER);
        INSERT OR IGNORE INTO settings VALUES(1,6);
        ''')
        if 'auth_version' not in {r['name'] for r in c.execute('PRAGMA table_info(users)')}:
            c.execute('ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0')
        if 'deleted_at' not in {r['name'] for r in c.execute('PRAGMA table_info(members)')}:
            c.execute('ALTER TABLE members ADD COLUMN deleted_at TEXT')
        # Non-destructive migration: old members remain unlinked.
        if 'user_id' not in {r['name'] for r in c.execute('PRAGMA table_info(members)')}:
            c.execute('ALTER TABLE members ADD COLUMN user_id INTEGER REFERENCES users(id)')
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS members_user_id ON members(user_id)')
        for months, price in [(1,500000),(3,1200000),(6,2000000),(12,3500000)]:
            c.execute('INSERT OR IGNORE INTO packages(months,price) VALUES(?,?)',(months,price))
        for name,role in [('admin','admin'),('letan','reception'),('hlv','trainer'),('thungan','cashier')]:
            c.execute('INSERT OR IGNORE INTO users(username,password,role) VALUES(?,?,?)',(name,generate_password_hash(os.getenv('DEMO_PASSWORD','Gym@12345')),role))
        if not c.execute('SELECT 1 FROM exercises').fetchone():
            c.executemany('INSERT INTO exercises(name) VALUES(?)',[(x,) for x in ['Squat','Bench press','Deadlift','Chạy bộ']])

def require(*roles):
    def deco(f):
        @wraps(f)
        def wrapped(*a,**kw):
            if not session.get('uid'): return redirect(url_for('login'))
            with db() as c:
                user = c.execute('SELECT role,auth_version FROM users WHERE id=?', (session['uid'],)).fetchone()
                archived = c.execute('SELECT 1 FROM members WHERE user_id=? AND deleted_at IS NOT NULL', (session['uid'],)).fetchone()
            if not user or archived or session.get('auth_version', 0) != user['auth_version']:
                session.clear()
                return redirect(url_for('login'))
            session['role'] = user['role']
            if roles and session['role'] not in roles and session['role']!='admin': abort(403)
            return f(*a,**kw)
        return wrapped
    return deco

@app.before_request
def csrf():
    session.setdefault('csrf',secrets.token_hex(24))
    if request.method=='POST' and not secrets.compare_digest(session['csrf'],request.form.get('csrf','')): abort(400)

@app.context_processor
def context():
    return dict(today=date.today().isoformat(),role=session.get('role'),csrf=session.get('csrf'))

def add_months(d,n):
    m=d.month-1+n; y=d.year+m//12; m=m%12+1
    return date(y,m,min(d.day,calendar.monthrange(y,m)[1]))

def normalize_phone(value):
    phone = re.sub(r'[\s().-]', '', value or '')
    if phone.startswith('+84'):
        phone = '0' + phone[3:]
    return phone if re.fullmatch(r'[0-9]{9,15}', phone) else ''


def valid_email(email):
    return not email or (len(email) <= 254 and re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", email) is not None)


def confirmation(email,name):
    if not email: return 'Bạn chưa thêm email; có thể bổ sung tại trang cá nhân để nhận xác nhận.'
    host=os.getenv('SMTP_HOST')
    if not host: return 'Chưa gửi email: chưa cấu hình SMTP.'
    try:
        msg=EmailMessage(); msg['Subject']='Xác nhận đăng ký hội viên Gym'; msg['From']=os.environ['SMTP_FROM']; msg['To']=email
        msg.set_content(f'Xin chào {name}, đăng ký hội viên của bạn đã được ghi nhận. Vui lòng thanh toán để kích hoạt gói tập.')
        with smtplib.SMTP(host,int(os.getenv('SMTP_PORT','587')),timeout=10) as s:
            s.starttls(); s.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']); s.send_message(msg)
        return 'Đã gửi email xác nhận.'
    except Exception:
        app.logger.exception('SMTP failed')
        return 'Đăng ký đã lưu nhưng gửi email thất bại. Hãy liên hệ lễ tân.'

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        identifier = request.form.get('username', '').strip()
        with db() as c:
            u = c.execute("SELECT * FROM users WHERE username=? AND role!='member'", (identifier.lower(),)).fetchone()
            if not u:
                phone = normalize_phone(identifier)
                candidates = c.execute("SELECT u.*,m.phone FROM users u JOIN members m ON m.user_id=u.id WHERE u.role='member' AND m.deleted_at IS NULL").fetchall() if phone else []
                matches = [row for row in candidates if normalize_phone(row['phone']) == phone]
                # Never guess between legacy profiles sharing a phone number.
                u = matches[0] if len(matches) == 1 else None
        with db() as c:
            archived = c.execute('SELECT 1 FROM members WHERE user_id=? AND deleted_at IS NOT NULL', (u['id'],)).fetchone() if u else None
        if u and not archived and check_password_hash(u['password'],request.form['password']):
            session.clear()
            session.update(uid=u['id'],role=u['role'],username=u['username'],auth_version=u['auth_version'],csrf=secrets.token_hex(24))
            return redirect('/account' if u['role']=='member' else '/')
        flash('Sai tài khoản hoặc mật khẩu.')
    return render_template('login.html')

@app.post('/logout')
def logout():
    session.clear(); return redirect('/login')

@app.route('/register',methods=['GET','POST'])
@require('reception','member')
def register():
    if session['role']=='member': return redirect('/account')
    with db() as c:
        packages=c.execute('SELECT * FROM packages ORDER BY months').fetchall()
        if request.method=='POST':
            try:
                f=request.form; name=f['name'].strip(); email=f['email'].strip(); phone=normalize_phone(f['phone']); birth=int(f['birth'])
                if not name or len(name)>120 or not valid_email(email) or not phone or not 1900<=birth<=date.today().year or f['gender'] not in ['Nam','Nữ','Khác']: raise ValueError()
                p=c.execute('SELECT * FROM packages WHERE id=?',(f['package'],)).fetchone()
                if not p: raise ValueError()
                d=date.today().isoformat(); source='Tại quầy' if session.get('role') in ['admin','reception'] else 'Trực tuyến'
                mid=c.execute('INSERT INTO members(name,gender,birth,phone,email,registered,source) VALUES(?,?,?,?,?,?,?)',(name,f['gender'],birth,phone,email,d,source)).lastrowid
                c.execute('INSERT INTO invoices(member,months,amount,created) VALUES(?,?,?,?)',(mid,p['months'],p['price'],d)); c.commit()
                flash(f'Đăng ký thành công. Mã hội viên: {mid}. '+confirmation(email,name)); return redirect('/register')
            except (ValueError,KeyError): flash('Thông tin không hợp lệ. Kiểm tra năm sinh, email và số điện thoại.')
    return render_template('register.html',packages=packages)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('uid'): return redirect('/')
    if request.method == 'POST':
        f = request.form
        try:
            name = f.get('name', '').strip()
            email = f.get('email', '').strip().lower()
            password = f.get('password', '')
            phone = normalize_phone(f.get('phone', ''))
            birth = int(f.get('birth', ''))
            gender = f.get('gender', '')
            if (not name or len(name)>120 or not valid_email(email)
                or not 8 <= len(password) <= 128 or password != f.get('confirm_password')
                or not phone
                or not 1900<=birth<=date.today().year or gender not in ['Nam','Nữ','Khác']):
                raise ValueError()
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                # Only current profiles reserve phone numbers; archived history stays separate.
                if any(normalize_phone(row['phone']) == phone for row in c.execute('SELECT phone FROM members WHERE deleted_at IS NULL')):
                    flash('Số điện thoại đã có hồ sơ hội viên. Vui lòng đăng nhập hoặc liên hệ lễ tân.')
                    return render_template('signup.html')
                uid = c.execute("INSERT INTO users(username,password,role) VALUES(?,?,'member')",
                                ('member:' + secrets.token_hex(16), generate_password_hash(password))).lastrowid
                c.execute('INSERT INTO members(name,gender,birth,phone,email,registered,source,user_id) VALUES(?,?,?,?,?,?,?,?)',
                          (name,gender,birth,phone,email,date.today().isoformat(),'Trực tuyến',uid))
            flash('Tạo tài khoản thành công! Hãy đăng nhập bằng số điện thoại để chọn gói tập.')
            return redirect('/login')
        except (ValueError, sqlite3.IntegrityError):
            flash('Không thể tạo tài khoản. Kiểm tra thông tin, số điện thoại đã dùng và mật khẩu khớp nhau (8–128 ký tự).')
    return render_template('signup.html')


@app.route('/account', methods=['GET', 'POST'])
@require('member')
def account():
    # Admin bypass in require() is appropriate for staff routes, not a member identity.
    if session['role'] != 'member': abort(403)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        member = c.execute('SELECT m.*,u.username trainer_name FROM members m LEFT JOIN users u ON u.id=m.trainer WHERE m.user_id=? AND m.deleted_at IS NULL', (session['uid'],)).fetchone()
        if not member: abort(403)
        if request.method == 'POST':
            if request.form.get('action') == 'email':
                email = request.form.get('email', '').strip().lower()
                if not valid_email(email):
                    flash('Email không hợp lệ. Để trống nếu không muốn thêm email.')
                else:
                    c.execute('UPDATE members SET email=? WHERE id=?', (email, member['id']))
                    flash('Đã cập nhật email.' if email else 'Đã bỏ email khỏi hồ sơ.')
                return redirect('/account')
            package = c.execute('SELECT * FROM packages WHERE id=?', (request.form.get('package',''),)).fetchone()
            pending = c.execute('SELECT 1 FROM invoices WHERE member=? AND paid_at IS NULL', (member['id'],)).fetchone()
            if not package:
                flash('Gói tập không hợp lệ.')
            elif pending:
                flash('Bạn đã có hóa đơn chờ thanh toán. Vui lòng liên hệ thu ngân.')
            else:
                c.execute('INSERT INTO invoices(member,months,amount,created) VALUES(?,?,?,?)',
                          (member['id'],package['months'],package['price'],date.today().isoformat()))
                c.commit()
                flash('Đã đăng ký gói tập. Vui lòng thanh toán tại quầy. '+confirmation(member['email'],member['name']))
            return redirect('/account')
        invoices = c.execute('SELECT * FROM invoices WHERE member=? ORDER BY id DESC', (member['id'],)).fetchall()
        plans = c.execute('SELECT p.*,e.name exercise_name FROM plans p JOIN exercises e ON e.id=p.exercise WHERE p.member=?', (member['id'],)).fetchall()
        active = c.execute('SELECT * FROM invoices WHERE member=? AND paid_at IS NOT NULL AND starts<=? AND expires>? ORDER BY expires DESC LIMIT 1',
                           (member['id'],date.today().isoformat(),date.today().isoformat())).fetchone()
        packages = c.execute('SELECT * FROM packages ORDER BY months').fetchall()
    return render_template('account.html',member=member,invoices=invoices,plans=plans,active=active,packages=packages,
                           pending=any(not i['paid_at'] for i in invoices))


@app.route('/account/password', methods=['GET', 'POST'])
@require('member')
def change_password():
    if session['role'] != 'member': abort(403)
    if request.method == 'POST':
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            user = c.execute('SELECT * FROM users WHERE id=?', (session['uid'],)).fetchone()
            f = request.form
            password = f.get('password', '')
            if not check_password_hash(user['password'], f.get('current_password', '')):
                flash('Mật khẩu hiện tại không đúng.')
            elif not 8 <= len(password) <= 128 or password != f.get('confirm_password'):
                flash('Mật khẩu mới phải có 8–128 ký tự và khớp với phần nhập lại.')
            elif check_password_hash(user['password'], password):
                flash('Mật khẩu mới phải khác mật khẩu hiện tại.')
            else:
                c.execute('UPDATE users SET password=?,auth_version=auth_version+1 WHERE id=?',
                          (generate_password_hash(password), user['id']))
                session.clear()
                flash('Đổi mật khẩu thành công. Vui lòng đăng nhập lại bằng mật khẩu mới.')
                return redirect('/login')
    return render_template('password.html', member=None)


@app.route('/members/<int:mid>/password', methods=['GET', 'POST'])
@require('admin')
def reset_member_password(mid):
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        member = c.execute("SELECT m.* FROM members m JOIN users u ON u.id=m.user_id WHERE m.id=? AND m.deleted_at IS NULL AND u.role='member'", (mid,)).fetchone()
        if not member: abort(404)
        if request.method == 'POST':
            f = request.form
            password = f.get('password', '')
            admin = c.execute('SELECT password FROM users WHERE id=?', (session['uid'],)).fetchone()
            if not check_password_hash(admin['password'], f.get('current_password', '')):
                flash('Mật khẩu quản trị viên không đúng.')
            elif not 8 <= len(password) <= 128 or password != f.get('confirm_password'):
                flash('Mật khẩu mới phải có 8–128 ký tự và khớp với phần nhập lại.')
            else:
                c.execute('UPDATE users SET password=?,auth_version=auth_version+1 WHERE id=?',
                          (generate_password_hash(password), member['user_id']))
                flash(f"Đã đặt lại mật khẩu cho hội viên #{mid}. Các phiên đăng nhập cũ đã bị đăng xuất.")
                return redirect('/members')
    return render_template('password.html', member=member)


@app.get('/')
@require()
def dashboard():
    if session['role']=='member': return redirect('/account')
    with db() as c:
        members=c.execute('SELECT count(*) FROM members WHERE deleted_at IS NULL').fetchone()[0]
        active=c.execute('SELECT count(DISTINCT member) FROM invoices WHERE paid_at IS NOT NULL AND starts<=? AND expires>? AND member IN (SELECT id FROM members WHERE deleted_at IS NULL)',(date.today().isoformat(),date.today().isoformat())).fetchone()[0]
        revenue=c.execute('SELECT coalesce(sum(amount),0) FROM invoices WHERE substr(paid_at,1,7)=?',(date.today().isoformat()[:7],)).fetchone()[0]
        year=str(date.today().year)
        counts=dict(c.execute('SELECT substr(registered,6,2),count(*) FROM members WHERE deleted_at IS NULL AND substr(registered,1,4)=? GROUP BY 1',(year,)).fetchall())
        totals=dict(c.execute('SELECT substr(paid_at,6,2),sum(amount) FROM invoices WHERE substr(paid_at,1,4)=? GROUP BY 1',(year,)).fetchall())
    return render_template('dashboard.html',members=members,active=active,revenue=revenue,year=year,counts=[counts.get(f'{i:02}',0) for i in range(1,13)],totals=[totals.get(f'{i:02}',0) for i in range(1,13)])

@app.route('/members',methods=['GET','POST'])
@require('reception')
def members():
    with db() as c:
        if request.method=='POST':
            trainer=request.form.get('trainer') or None
            if trainer and not c.execute("SELECT 1 FROM users WHERE id=? AND role='trainer'",(trainer,)).fetchone(): abort(400)
            c.execute('UPDATE members SET trainer=? WHERE id=? AND deleted_at IS NULL',(trainer,request.form['member'])); flash('Đã cập nhật huấn luyện viên.')
        rows=c.execute('SELECT m.*,u.username trainer_name FROM members m LEFT JOIN users u ON u.id=m.trainer WHERE m.deleted_at IS NULL ORDER BY m.id DESC').fetchall()
        trainers=c.execute("SELECT * FROM users WHERE role='trainer'").fetchall()
    return render_template('members.html',rows=rows,trainers=trainers)


@app.route('/members/<int:mid>/delete', methods=['GET', 'POST'])
@require('reception')
def delete_member(mid):
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        member = c.execute('SELECT * FROM members WHERE id=? AND deleted_at IS NULL', (mid,)).fetchone()
        if not member: abort(404)
        if request.method == 'POST':
            if request.form.get('confirm') != str(mid):
                flash('Nhập đúng mã hội viên để xác nhận xóa.')
            else:
                c.execute('UPDATE members SET deleted_at=? WHERE id=?', (datetime.now().isoformat(), mid))
                flash('Đã xóa hội viên khỏi danh sách và khóa đăng nhập. Lịch sử thanh toán được giữ lại.')
                return redirect('/members')
    return render_template('delete_member.html', member=member)

@app.route('/payments',methods=['GET','POST'])
@require('cashier')
def payments():
    with db() as c:
        if request.method=='POST':
            c.execute('BEGIN IMMEDIATE')
            inv=c.execute('SELECT * FROM invoices WHERE id=?',(request.form['invoice'],)).fetchone()
            if not inv: abort(404)
            if c.execute('SELECT 1 FROM members WHERE id=? AND deleted_at IS NOT NULL',(inv['member'],)).fetchone():
                flash('Hội viên đã bị xóa. Không thể thu thêm tiền.')
                return redirect('/payments')
            if not inv['paid_at']:
                d=date.today(); last=c.execute('SELECT max(expires) FROM invoices WHERE member=? AND paid_at IS NOT NULL',(inv['member'],)).fetchone()[0]
                start=max(d,date.fromisoformat(last)) if last else d
                c.execute('UPDATE invoices SET paid_at=?,starts=?,expires=? WHERE id=? AND paid_at IS NULL',(d.isoformat(),start.isoformat(),add_months(start,inv['months']).isoformat(),inv['id'])); flash('Đã xác nhận thu tiền, kích hoạt gói tập.')
        rows=c.execute('SELECT i.*,m.name FROM invoices i JOIN members m ON m.id=i.member ORDER BY i.id DESC').fetchall()
    return render_template('payments.html',rows=rows)

@app.route('/plans',methods=['GET','POST'])
@require('trainer')
def plans():
    with db() as c:
        allowed=c.execute('SELECT * FROM members WHERE deleted_at IS NULL AND (trainer=? OR ?=\'admin\')',(session['uid'],session['role'])).fetchall()
        limit=c.execute('SELECT max_days FROM settings').fetchone()[0]
        if request.method=='POST':
            try:
                mid=int(request.form['member']); days=sorted(set(request.form.getlist('days'))); sets=int(request.form['sets']); reps=int(request.form['reps']); eid=int(request.form['exercise'])
                existing=set()
                for row in c.execute('SELECT days FROM plans WHERE member=?',(mid,)): existing.update(row['days'].split(','))
                if mid not in [m['id'] for m in allowed] or not days or not set(days)<=set('2345678') or len(existing|set(days))>limit or not 1<=sets<=100 or not 1<=reps<=1000 or not c.execute('SELECT 1 FROM exercises WHERE id=? AND active=1',(eid,)).fetchone(): raise ValueError()
                c.execute('INSERT INTO plans(member,exercise,sets,reps,days) VALUES(?,?,?,?,?)',(mid,eid,sets,reps,','.join(days))); flash('Đã thêm bài tập.')
            except (ValueError,KeyError): flash(f'Không hợp lệ: tổng số ngày tập của hội viên phải tối đa {limit} ngày/tuần.')
        rows=c.execute("SELECT p.*,m.name,e.name exercise_name FROM plans p JOIN members m ON m.id=p.member JOIN exercises e ON e.id=p.exercise WHERE m.deleted_at IS NULL AND (m.trainer=? OR ?='admin')",(session['uid'],session['role'])).fetchall()
        exercises=c.execute('SELECT * FROM exercises WHERE active=1').fetchall()
    return render_template('plans.html',rows=rows,members=allowed,exercises=exercises,limit=limit)

@app.post('/plans/<int:pid>/delete')
@require('trainer')
def delete_plan(pid):
    with db() as c:
        c.execute("DELETE FROM plans WHERE id=? AND member IN (SELECT id FROM members WHERE trainer=? OR ?='admin')",(pid,session['uid'],session['role']))
    return redirect('/plans')

@app.route('/settings',methods=['GET','POST'])
@require('admin')
def settings():
    with db() as c:
        if request.method=='POST':
            try:
                f=request.form
                if f['action']=='price':
                    price=int(f['price'])
                    if price<=0: raise ValueError()
                    c.execute('UPDATE packages SET price=? WHERE id=?',(price,f['id']))
                elif f['action']=='limit':
                    n=int(f['limit'])
                    if not 1<=n<=7: raise ValueError()
                    for m in c.execute('SELECT DISTINCT member FROM plans'):
                        days=set()
                        for r in c.execute('SELECT days FROM plans WHERE member=?',(m['member'],)): days.update(r['days'].split(','))
                        if len(days)>n: raise ValueError()
                    c.execute('UPDATE settings SET max_days=?',(n,))
                elif f['action'] in ['add','edit']:
                    name=f['name'].strip()
                    if not name or len(name)>100: raise ValueError()
                    if f['action']=='add': c.execute('INSERT INTO exercises(name) VALUES(?)',(name,))
                    else: c.execute('UPDATE exercises SET name=? WHERE id=?',(name,f['id']))
                elif f['action']=='delete': c.execute('UPDATE exercises SET active=0 WHERE id=?',(f['id'],))
                else: raise ValueError()
                flash('Đã lưu. Giá mới chỉ áp dụng cho hóa đơn tạo sau này.')
            except (ValueError,sqlite3.IntegrityError): flash('Dữ liệu không hợp lệ hoặc trùng tên. Khi giảm số ngày, hãy sửa lịch đang vượt giới hạn trước.')
        packages=c.execute('SELECT * FROM packages').fetchall(); exercises=c.execute('SELECT * FROM exercises WHERE active=1').fetchall(); limit=c.execute('SELECT max_days FROM settings').fetchone()[0]
    return render_template('settings.html',packages=packages,exercises=exercises,limit=limit)

# Flask CLI/PyCharm imports this module without running the __main__ block.
# Initialize and migrate the database for both supported launch methods.
init_db()

if __name__=='__main__':
    app.run(host='127.0.0.1',port=5000,debug=os.getenv('FLASK_DEBUG')=='1')

