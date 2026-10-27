import tempfile, unittest, sqlite3
from pathlib import Path
from unittest.mock import patch
from werkzeug.security import check_password_hash, generate_password_hash
from index import app, init_db, db, confirmation as real_confirmation

class MemberFlow(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  app.config.update(TESTING=True,DATABASE=str(Path(self.tmp.name)/'test.db'))
  init_db()
  with db() as c:
   c.execute("INSERT INTO users(username,password,role) VALUES(?,?,'trainer')",('hlv',generate_password_hash('Gym@12345')))
  self.c=app.test_client()
  self.mail=patch('index.confirmation',return_value='SMTP test'); self.send=self.mail.start()
 def tearDown(self): self.mail.stop(); self.tmp.cleanup()
 def post(self,path,data,client=None):
  client=client or self.c
  with client.session_transaction() as s: s.setdefault('csrf','test'); token=s['csrf']
  return client.post(path,data={**data,'csrf':token})
 def signup(self,email='a@example.com',**kw):
  data=dict(name='Hoi Vien A',email=email,phone='0901234567',gender='Nam',birth=2000,password='Member12345',confirm_password='Member12345');data.update(kw)
  return self.post('/signup',data)
 def login(self,user='0901234567',password='Member12345',client=None):
  return self.post('/login',dict(username=user,password=password),client)
 def test_account_first_and_payment(self):
  self.assertEqual(self.c.get('/register').status_code,302)
  self.assertEqual(self.signup().status_code,302)
  with db() as c:
   self.assertEqual(c.execute('SELECT count(*) FROM invoices').fetchone()[0],0)
   u=c.execute("SELECT * FROM users WHERE role='member'").fetchone()
   self.assertTrue(check_password_hash(u['password'],'Member12345'))
  self.assertEqual(self.send.call_count,0)
  self.assertTrue(self.login().location.endswith('/account'))
  for path in ['/account','/signup','/register','/']: self.assertIn(self.c.get(path).status_code,[200,302])
  for path in ['/members','/payments','/plans','/settings']: self.assertEqual(self.c.get(path).status_code,403)
  self.post('/account',{'package':1,'member':999})
  self.post('/account',{'package':1})
  with db() as c: self.assertEqual(c.execute('SELECT count(*) FROM invoices').fetchone()[0],1)
  self.assertEqual(self.send.call_count,1)
  staff=app.test_client();self.login('letan','Gym@12345',staff)
  self.post('/payments',{'invoice':1},staff)
  self.assertIn('Đang hoạt động',self.c.get('/account').get_data(as_text=True))
  self.post('/account',{'package':2})
  with db() as c: self.assertEqual(c.execute('SELECT count(*) FROM invoices').fetchone()[0],2)
 def test_validation_and_csrf(self):
  self.assertEqual(self.c.post('/signup',data={}).status_code,400)
  self.signup(password='short',confirm_password='short')
  self.signup(confirm_password='different')
  self.signup(email='bad')
  self.signup()
  self.signup(email='A@EXAMPLE.COM')
  with db() as c: self.assertEqual(c.execute("SELECT count(*) FROM users WHERE role='member'").fetchone()[0],1)
  self.assertEqual(self.login(password='wrong').status_code,200)
  self.login();self.post('/account',{'package':'999'})
  with db() as c: self.assertEqual(c.execute('SELECT count(*) FROM invoices').fetchone()[0],0)
 def test_member_isolation(self):
  self.signup();self.signup(email='b@example.com',name='Secret B',phone='0901234568')
  with db() as c:
   b=c.execute("SELECT id FROM members WHERE email='b@example.com'").fetchone()[0]
   c.execute('INSERT INTO invoices(member,months,amount,created) VALUES(?,12,3456789,?)',(b,'2026-01-01'))
   c.execute('INSERT INTO plans(member,exercise,sets,reps,days) VALUES(?,1,99,99,?)',(b,'2'))
  self.login();page=self.c.get('/account?member='+str(b)).get_data(as_text=True)
  self.assertNotIn('Secret B',page);self.assertNotIn('3,456,789',page);self.assertNotIn('Squat',page)
  self.post('/account',{'package':1,'member':b})
  with db() as c: self.assertEqual(c.execute('SELECT count(*) FROM invoices WHERE member=?',(b,)).fetchone()[0],1)
 def test_existing_data_migration(self):
  legacy=Path(self.tmp.name)/'legacy.db'
  with sqlite3.connect(legacy) as c:
   c.execute('CREATE TABLE members(id INTEGER PRIMARY KEY,name TEXT,gender TEXT,birth INTEGER,phone TEXT,email TEXT,registered TEXT,source TEXT,trainer INTEGER REFERENCES users(id))')
   c.execute("INSERT INTO members VALUES(1,'Old Member','Nam',2000,'0901234567','old@example.com','2026-01-01','Tại quầy',NULL)")
  app.config['DATABASE']=str(legacy);init_db();init_db()
  self.signup(email='old@example.com')
  with db() as c:
   self.assertEqual(c.execute('SELECT count(*) FROM members').fetchone()[0],1)
   self.assertIsNone(c.execute('SELECT user_id FROM members').fetchone()[0])
  self.login('admin','Gym@12345')
  for path in ['/','/members','/payments','/settings','/register']:
   self.assertEqual(self.c.get(path).status_code,200)
  self.assertEqual(self.c.get('/account').status_code,403)
  self.assertEqual(self.c.get('/plans').status_code,403)

 def test_delete_member_preserves_history_and_revokes_session(self):
  self.signup();self.login();self.post('/account',{'package':1})
  with db() as c:
   mid=c.execute("SELECT id FROM members WHERE email='a@example.com'").fetchone()[0]
   c.execute("UPDATE invoices SET paid_at='2026-01-01' WHERE member=?",(mid,))
  url=f'/members/{mid}/delete'
  self.assertEqual(self.post(url,{'confirm':str(mid)}).status_code,403)
  staff=app.test_client();self.login('letan','Gym@12345',staff)
  self.assertEqual(staff.get(url).status_code,200)
  self.assertEqual(staff.post(url,data={'confirm':str(mid)}).status_code,400)
  self.post(url,{'confirm':'wrong'},staff)
  with db() as c: self.assertIsNone(c.execute('SELECT deleted_at FROM members WHERE id=?',(mid,)).fetchone()[0])
  self.assertEqual(self.post(url,{'confirm':str(mid)},staff).status_code,302)
  self.assertNotIn('a@example.com',staff.get('/members').get_data(as_text=True))
  self.assertEqual(self.c.get('/account').status_code,302)
  self.assertEqual(self.login().status_code,200)
  with db() as c:
   self.assertEqual(c.execute('SELECT sum(amount) FROM invoices WHERE paid_at IS NOT NULL').fetchone()[0],500000)
   self.assertIsNotNone(c.execute('SELECT deleted_at FROM members WHERE id=?',(mid,)).fetchone()[0])
  self.assertEqual(self.post(url,{'confirm':str(mid)},staff).status_code,404)
  for user in ['hlv']:
   other=app.test_client();self.login(user,'Gym@12345',other)
   self.assertEqual(self.post(url,{'confirm':str(mid)},other).status_code,403)

 def test_optional_email_and_phone_login(self):
  self.assertEqual(self.signup(email='').status_code,302)
  self.assertEqual(self.login(user='a@example.com').status_code,200)
  self.assertEqual(self.login(user='+84 901-234-567').status_code,302)
  self.assertIn('Chưa thêm email',self.c.get('/account').get_data(as_text=True))
  self.post('/account',{'action':'email','email':'new@gmail.com','member':999})
  with db() as c:
   self.assertEqual(c.execute('SELECT email FROM members').fetchone()[0],'new@gmail.com')
   self.assertEqual(c.execute('SELECT count(*) FROM invoices').fetchone()[0],0)
  self.post('/account',{'action':'email','email':'invalid'})
  with db() as c: self.assertEqual(c.execute('SELECT email FROM members').fetchone()[0],'new@gmail.com')
  self.post('/account',{'action':'email','email':''})
  with db() as c: self.assertEqual(c.execute('SELECT email FROM members').fetchone()[0],'')
  self.post('/logout',{})
  self.signup(email='other@gmail.com',phone='+84 901 234 567')
  with db() as c: self.assertEqual(c.execute("SELECT count(*) FROM users WHERE role='member'").fetchone()[0],1)
  self.signup(email='',phone='0901234568')
  with db() as c: self.assertEqual(c.execute("SELECT count(*) FROM users WHERE role='member'").fetchone()[0],2)

 def test_legacy_email_account_logs_in_by_phone(self):
  self.signup()
  with db() as c: c.execute("UPDATE users SET username='a@example.com' WHERE role='member'")
  self.assertEqual(self.login().status_code,302)
  self.post('/logout',{})
  self.assertEqual(self.login('a@example.com').status_code,200)
  with db() as c:
   uid=c.execute("INSERT INTO users(username,password,role) SELECT 'duplicate',password,'member' FROM users WHERE role='member'").lastrowid
   c.execute("INSERT INTO members(name,phone,user_id) VALUES('Duplicate','0901234567',?)",(uid,))
  self.assertEqual(self.login().status_code,200)

 def test_no_smtp_without_email(self):
  with patch('index.smtplib.SMTP') as smtp:
   self.assertIn('chưa thêm email',real_confirmation('', 'Test'))
   smtp.assert_not_called()

 def test_reuse_deleted_phone_keeps_old_history_private(self):
  self.signup(name='Old Person');self.login();self.post('/account',{'package':1})
  with db() as c:
   old=c.execute('SELECT id,user_id FROM members').fetchone()
   # Reproduce accounts from the previous phone-as-username version.
   c.execute('UPDATE users SET username=? WHERE id=?',('0901234567',old['user_id']))
   c.execute("UPDATE invoices SET paid_at='2026-01-01' WHERE member=?",(old['id'],))
   c.execute("INSERT INTO plans(member,exercise,sets,reps,days) VALUES(?,1,3,15,'2')",(old['id'],))
  staff=app.test_client();self.login('letan','Gym@12345',staff)
  self.post(f"/members/{old['id']}/delete",{'confirm':str(old['id'])},staff)
  newclient=app.test_client()
  self.c=newclient
  self.assertEqual(self.signup(email='',name='New Person',phone='+84 901 234 567',password='NewPass123',confirm_password='NewPass123').status_code,302)
  self.assertEqual(self.login().status_code,200)  # Old password must not access the new account.
  self.assertEqual(self.login(password='NewPass123').status_code,302)
  page=self.c.get('/account').get_data(as_text=True)
  self.assertIn('New Person',page);self.assertNotIn('Old Person',page);self.assertNotIn('Squat',page)
  self.assertIn('Chưa có hóa đơn.',page)
  self.signup()  # Logged-in signup cannot create another profile.
  with db() as c:
   self.assertEqual(c.execute('SELECT count(*) FROM members WHERE deleted_at IS NULL').fetchone()[0],1)
   self.assertEqual(c.execute('SELECT member FROM invoices').fetchone()[0],old['id'])
   self.assertEqual(c.execute('SELECT sum(amount) FROM invoices').fetchone()[0],500000)
  oldclient=app.test_client()
  with oldclient.session_transaction() as session: session.update(uid=old['user_id'],role='member')
  self.assertEqual(oldclient.get('/account').status_code,302)

 def test_member_password_change_and_old_sessions(self):
  self.signup();self.signup(phone='0901234568',name='Other',email='b@example.com')
  self.login();other_session=app.test_client();self.login(client=other_session)
  url='/account/password'
  self.assertEqual(self.c.get(url).status_code,200)
  self.assertIn('Đổi mật khẩu',self.c.get('/account').get_data(as_text=True))
  self.assertEqual(self.c.post(url,data={}).status_code,400)
  for current,password,confirm in [('wrong','NewPass123','NewPass123'),('Member12345','short','short'),('Member12345','NewPass123','Mismatch'),('Member12345','Member12345','Member12345')]:
   self.assertEqual(self.post(url,dict(current_password=current,password=password,confirm_password=confirm)).status_code,200)
  self.assertTrue(self.post(url,dict(current_password='Member12345',password='NewPass123',confirm_password='NewPass123',user_id=999)).location.endswith('/login'))
  self.assertEqual(other_session.get('/account').status_code,302)
  self.assertEqual(self.login().status_code,200)
  self.assertEqual(self.login(password='NewPass123').status_code,302)
  self.assertEqual(self.login('0901234568').status_code,302)
  with db() as c:
   row=c.execute("SELECT u.* FROM users u JOIN members m ON m.user_id=u.id WHERE m.phone='0901234567'").fetchone()
   self.assertNotEqual(row['password'],'NewPass123');self.assertTrue(check_password_hash(row['password'],'NewPass123'))
   self.assertEqual(row['auth_version'],1)

 def test_admin_resets_member_password_only(self):
  self.signup();self.login();member_client=self.c
  with db() as c: mid=c.execute('SELECT id FROM members').fetchone()[0]
  url=f'/members/{mid}/password'
  self.assertEqual(self.post(url,{}).status_code,403)
  for user in ['hlv']:
   staff=app.test_client();self.login(user,'Gym@12345',staff)
   self.assertEqual(staff.get(url).status_code,403)
   self.assertEqual(self.post(url,{},staff).status_code,403)
  admin=app.test_client();self.login('admin','Gym@12345',admin)
  self.assertEqual(admin.get(url).status_code,200)
  self.assertIn('Đặt lại mật khẩu',admin.get('/members').get_data(as_text=True))
  self.assertEqual(admin.post(url,data={}).status_code,400)
  data=dict(current_password='wrong',password='ResetPass123',confirm_password='ResetPass123')
  self.assertEqual(self.post(url,data,admin).status_code,200)
  data['current_password']='Gym@12345';data['confirm_password']='Mismatch'
  self.assertEqual(self.post(url,data,admin).status_code,200)
  data['confirm_password']='ResetPass123'
  self.assertTrue(self.post(url,data,admin).location.endswith('/members'))
  self.assertEqual(member_client.get('/account').status_code,302)
  self.assertEqual(self.login().status_code,200)
  self.assertEqual(self.login(password='ResetPass123').status_code,302)
  self.assertEqual(admin.get('/members').status_code,200)
  self.assertEqual(admin.get('/account/password').status_code,403)
  self.assertEqual(admin.get('/members/99999/password').status_code,404)
  self.post(f'/members/{mid}/delete',{'confirm':str(mid)},admin)
  self.assertEqual(self.post(url,data,admin).status_code,404)
  with db() as c:
   legacy=c.execute("INSERT INTO members(name,phone) VALUES('No account','0900000000')").lastrowid
  self.assertEqual(admin.get(f'/members/{legacy}/password').status_code,404)

 def test_reception_collects_payment_and_resets_password(self):
  self.signup();self.login();self.post('/account',{'package':1})
  member_client=self.c
  with db() as c: mid=c.execute('SELECT id FROM members').fetchone()[0]
  reception=app.test_client();self.login('letan','Gym@12345',reception)
  self.assertIn('Thanh toán',reception.get('/').get_data(as_text=True))
  self.assertEqual(reception.get('/payments').status_code,200)
  self.assertEqual(self.post('/payments',{'invoice':1},reception).status_code,200)
  self.assertIn('Đặt lại mật khẩu',reception.get('/members').get_data(as_text=True))
  data=dict(current_password='wrong',password='Reception123',confirm_password='Reception123')
  self.assertEqual(self.post(f'/members/{mid}/password',data,reception).status_code,200)
  data['current_password']='Gym@12345'
  self.assertEqual(self.post(f'/members/{mid}/password',data,reception).status_code,302)
  self.assertEqual(member_client.get('/account').status_code,302)
  self.assertEqual(self.login(password='Reception123').status_code,302)
  with db() as c: self.assertIsNotNone(c.execute('SELECT paid_at FROM invoices').fetchone()[0])
  self.assertEqual(reception.get('/settings').status_code,403)

 def test_trainer_schedules_only_after_accepting_request(self):
  self.signup();self.login()
  with db() as c:
   mid=c.execute('SELECT id FROM members').fetchone()[0]
   trainer=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
  self.post('/account',dict(action='trainer_request',trainer=trainer,member=999))
  self.post('/account',dict(action='trainer_request',trainer=trainer))
  with db() as c:
   self.assertIsNone(c.execute('SELECT trainer FROM members').fetchone()[0])
   self.assertEqual(c.execute('SELECT count(*) FROM trainer_requests').fetchone()[0],1)
   rid=c.execute('SELECT id FROM trainer_requests').fetchone()[0]
  hlv=app.test_client();self.login('hlv','Gym@12345',hlv)
  self.assertNotIn('Hoi Vien A',hlv.get('/members').get_data(as_text=True))
  self.assertIn('Xác nhận làm HLV',hlv.get('/trainer-requests').get_data(as_text=True))
  data=dict(member=mid,exercise=1,sets=3,reps=15,days=['2','4','6'])
  self.post('/plans',data,hlv)
  with db() as c: self.assertEqual(c.execute('SELECT count(*) FROM plans').fetchone()[0],0)
  self.assertEqual(hlv.post(f'/trainer-requests/{rid}/respond',data={'decision':'accept'}).status_code,400)
  self.assertEqual(self.post(f'/trainer-requests/{rid}/respond',{'decision':'accept'},hlv).status_code,302)
  self.assertEqual(self.post('/plans',data,hlv).status_code,302)
  self.post(f'/trainer-requests/{rid}/respond',{'decision':'reject'},hlv)
  with db() as c:
   self.assertEqual(c.execute('SELECT trainer FROM members').fetchone()[0],trainer)
   self.assertEqual(c.execute('SELECT status FROM trainer_requests').fetchone()[0],'accepted')
   self.assertEqual(c.execute('SELECT count(*) FROM plans').fetchone()[0],1)
  self.assertIn('Squat',self.c.get('/account').get_data(as_text=True))
  self.assertIn('Đã được hlv xác nhận',self.c.get('/account').get_data(as_text=True))

 def test_cancel_reject_and_request_ownership(self):
  self.signup();self.login()
  with db() as c:
   trainer=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
   peer=c.execute("INSERT INTO users(username,password,role) SELECT 'hlv2',password,role FROM users WHERE username='hlv'").lastrowid
  self.post('/account',dict(action='trainer_request',trainer=1))  # admin is not a trainer
  with db() as c: self.assertEqual(c.execute('SELECT count(*) FROM trainer_requests').fetchone()[0],0)
  self.post('/account',dict(action='trainer_request',trainer=trainer))
  with db() as c: rid=c.execute('SELECT id FROM trainer_requests').fetchone()[0]
  peerclient=app.test_client();self.login('hlv2','Gym@12345',peerclient)
  self.assertEqual(self.post(f'/trainer-requests/{rid}/respond',{'decision':'accept'},peerclient).status_code,403)
  other=app.test_client()
  self.post('/logout',{});self.signup(phone='0901234568',email='b@example.com');self.login('0901234568',client=other)
  self.post('/account',dict(action='cancel_trainer_request',request_id=rid),other)
  with db() as c: self.assertEqual(c.execute('SELECT status FROM trainer_requests WHERE id=?',(rid,)).fetchone()[0],'pending')
  self.login();self.post('/account',dict(action='cancel_trainer_request',request_id=rid))
  hlv=app.test_client();self.login('hlv','Gym@12345',hlv)
  self.post(f'/trainer-requests/{rid}/respond',{'decision':'accept'},hlv)
  with db() as c: self.assertIsNone(c.execute("SELECT trainer FROM members WHERE phone='0901234567'").fetchone()[0])
  self.post('/account',dict(action='trainer_request',trainer=trainer))
  with db() as c: rid=c.execute('SELECT max(id) FROM trainer_requests').fetchone()[0]
  self.post(f'/trainer-requests/{rid}/respond',{'decision':'reject'},hlv)
  self.post('/account',dict(action='trainer_request',trainer=peer))
  with db() as c:
   self.assertEqual(c.execute("SELECT trainer FROM trainer_requests WHERE status='pending'").fetchone()[0],peer)
  self.assertEqual(self.c.get('/trainer-requests').status_code,403)

 def test_staff_request_does_not_bypass_confirmation(self):
  self.signup();self.login()
  with db() as c:
   mid=c.execute('SELECT id FROM members').fetchone()[0]
   trainer=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
  reception=app.test_client();self.login('letan','Gym@12345',reception)
  self.post('/members',dict(member=mid,trainer=trainer),reception)
  admin=app.test_client();self.login('admin','Gym@12345',admin)
  self.post('/plans',dict(member=mid,exercise=1,sets=3,reps=15,days=['2']),admin)
  with db() as c:
   self.assertIsNone(c.execute('SELECT trainer FROM members').fetchone()[0])
   self.assertEqual(c.execute('SELECT count(*) FROM plans').fetchone()[0],0)
   rid=c.execute('SELECT id FROM trainer_requests').fetchone()[0]
  self.assertEqual(self.post(f'/trainer-requests/{rid}/respond',{'decision':'accept'},admin).status_code,403)
  self.post(f'/members/{mid}/delete',{'confirm':str(mid)},reception)
  hlv=app.test_client();self.login('hlv','Gym@12345',hlv)
  self.assertEqual(self.post(f'/trainer-requests/{rid}/respond',{'decision':'accept'},hlv).status_code,404)
  with db() as c: self.assertEqual(c.execute('SELECT status FROM trainer_requests').fetchone()[0],'cancelled')

 def test_existing_assignment_requires_confirmation_after_migration(self):
  self.signup()
  with db() as c:
   trainer=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
   c.execute('UPDATE members SET trainer=?',(trainer,))
   c.execute("DELETE FROM app_migrations WHERE name='trainer-consent-v1'")
   c.execute("INSERT INTO plans(member,exercise,sets,reps,days) VALUES(1,1,3,15,'2')")
  init_db();init_db()
  with db() as c:
   self.assertIsNone(c.execute('SELECT trainer FROM members').fetchone()[0])
   self.assertEqual(c.execute('SELECT count(*) FROM trainer_requests').fetchone()[0],1)
   self.assertEqual(c.execute('SELECT count(*) FROM plans').fetchone()[0],1)
   rid=c.execute('SELECT id FROM trainer_requests').fetchone()[0]
  self.login('hlv','Gym@12345')
  self.post(f'/plans/1/delete',{})
  with db() as c: self.assertEqual(c.execute('SELECT count(*) FROM plans').fetchone()[0],1)
  self.post(f'/trainer-requests/{rid}/respond',{'decision':'accept'})
  init_db()
  with db() as c:
   self.assertEqual(c.execute('SELECT trainer FROM members').fetchone()[0],trainer)
   self.assertEqual(c.execute('SELECT count(*) FROM trainer_requests').fetchone()[0],1)

 def test_cashier_role_migrates_without_password_change(self):
  with db() as c:
   self.assertIsNone(c.execute("SELECT 1 FROM users WHERE username='thungan'").fetchone())
   c.execute("INSERT INTO users(username,password,role) SELECT 'thungan',password,'cashier' FROM users WHERE username='letan'")
   old=c.execute("SELECT password FROM users WHERE username='thungan'").fetchone()[0]
  init_db();init_db()
  with db() as c:
   row=c.execute("SELECT role,password FROM users WHERE username='thungan'").fetchone()
   self.assertEqual(row['role'],'reception');self.assertEqual(row['password'],old)
  self.assertEqual(self.login('thungan','Gym@12345').status_code,302)
  self.assertEqual(self.c.get('/payments').status_code,200)
  self.assertEqual(self.c.get('/members').status_code,200)

 def test_cancel_confirmed_trainer_and_choose_new_one(self):
  self.signup();self.login();self.post('/account',{'package':1})
  with db() as c:
   mid=c.execute('SELECT id FROM members').fetchone()[0]
   trainer=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
   peer=c.execute("INSERT INTO users(username,password,role) SELECT 'hlv2',password,role FROM users WHERE username='hlv'").lastrowid
   invoice=tuple(c.execute('SELECT * FROM invoices').fetchone())
   c.execute('UPDATE settings SET max_days=1')
  self.post('/account',dict(action='trainer_request',trainer=trainer))
  with db() as c: rid=c.execute('SELECT id FROM trainer_requests').fetchone()[0]
  hlv=app.test_client();self.login('hlv','Gym@12345',hlv)
  self.post(f'/trainer-requests/{rid}/respond',{'decision':'accept'},hlv)
  self.post('/plans',dict(member=mid,exercise=1,sets=3,reps=15,days=['2']),hlv)
  self.assertIn('Hủy đăng ký HLV',self.c.get('/account').get_data(as_text=True))
  self.assertEqual(self.c.get('/account/trainer/cancel').status_code,200)
  self.assertEqual(self.c.post('/account/trainer/cancel',data={'request_id':rid}).status_code,400)
  self.post('/account/trainer/cancel',{'request_id':99999})
  with db() as c: self.assertEqual(c.execute('SELECT trainer FROM members').fetchone()[0],trainer)
  self.assertEqual(self.post('/account/trainer/cancel',{'request_id':rid}).status_code,302)
  with db() as c:
   self.assertIsNone(c.execute('SELECT trainer FROM members').fetchone()[0])
   self.assertEqual(c.execute('SELECT status FROM trainer_requests').fetchone()[0],'cancelled')
   self.assertEqual(c.execute('SELECT active FROM plans').fetchone()[0],0)
   self.assertEqual(tuple(c.execute('SELECT * FROM invoices').fetchone()),invoice)
  self.assertNotIn('Squat',self.c.get('/account').get_data(as_text=True))
  self.post('/plans',dict(member=mid,exercise=1,sets=3,reps=15,days=['2']),hlv)
  self.post('/plans/1/delete',{},hlv)
  with db() as c: self.assertEqual(c.execute('SELECT count(*) FROM plans').fetchone()[0],1)
  self.post('/account',dict(action='trainer_request',trainer=peer))
  with db() as c: rid2=c.execute('SELECT max(id) FROM trainer_requests').fetchone()[0]
  hlv2=app.test_client();self.login('hlv2','Gym@12345',hlv2)
  self.post(f'/trainer-requests/{rid2}/respond',{'decision':'accept'},hlv2)
  self.post('/account/trainer/cancel',{'request_id':rid})  # Stale form cannot cancel a new HLV.
  with db() as c: self.assertEqual(c.execute('SELECT trainer FROM members').fetchone()[0],peer)
  self.assertEqual(self.post('/plans',dict(member=mid,exercise=2,sets=3,reps=15,days=['3']),hlv2).status_code,302)
  page=self.c.get('/account').get_data(as_text=True)
  self.assertIn('Bench press',page);self.assertNotIn('Squat',page)

 def test_cannot_cancel_another_members_trainer(self):
  self.signup();self.signup(phone='0901234568',email='b@example.com')
  with db() as c:
   trainer=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
  self.login();self.post('/account',dict(action='trainer_request',trainer=trainer))
  with db() as c: rid=c.execute('SELECT id FROM trainer_requests').fetchone()[0]
  hlv=app.test_client();self.login('hlv','Gym@12345',hlv)
  self.post(f'/trainer-requests/{rid}/respond',{'decision':'accept'},hlv)
  other=app.test_client();self.login('0901234568',client=other)
  self.post('/account/trainer/cancel',{'request_id':rid,'member':1},other)
  with db() as c: self.assertEqual(c.execute('SELECT trainer FROM members WHERE id=1').fetchone()[0],trainer)
  self.assertEqual(self.post('/account/trainer/cancel',{'request_id':rid},hlv).status_code,403)

 def test_trainer_roster_and_plan_picker_only_show_own_confirmed_members(self):
  with db() as c:
   trainer=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
   peer=c.execute("INSERT INTO users(username,password,role) SELECT 'hlv2',password,role FROM users WHERE username='hlv'").lastrowid
   cases=[('OwnConfirmed',trainer,'accepted',None),('PeerConfirmed',peer,'accepted',None),('UnassignedPerson',None,None,None),('PendingPerson',None,'pending',None),('CancelledPerson',None,'cancelled',None),('DeletedPerson',trainer,'accepted','2026-01-01'),('PointerWithoutConsent',trainer,None,None)]
   for name,owner,status,deleted in cases:
    mid=c.execute('INSERT INTO members(name,phone,trainer,deleted_at) VALUES(?,?,?,?)',(name,'0900000000',owner,deleted)).lastrowid
    if status:
     c.execute('INSERT INTO trainer_requests(member,trainer,status,created) VALUES(?,?,?,?)',(mid,owner or trainer,status,'2026-01-01'))
  self.login('hlv','Gym@12345')
  for path in ['/members','/plans','/plans?member=2']:
   page=self.c.get(path).get_data(as_text=True)
   self.assertIn('OwnConfirmed',page)
   for name in ['PeerConfirmed','UnassignedPerson','PendingPerson','CancelledPerson','DeletedPerson','PointerWithoutConsent']:
    self.assertNotIn(name,page)
  self.assertIn('PendingPerson',self.c.get('/trainer-requests').get_data(as_text=True))
  self.post('/logout',{});self.login('hlv2','Gym@12345')
  page=self.c.get('/members').get_data(as_text=True)
  self.assertIn('PeerConfirmed',page);self.assertNotIn('OwnConfirmed',page)
  self.post('/logout',{});self.login('letan','Gym@12345')
  page=self.c.get('/members').get_data(as_text=True)
  for name in ['OwnConfirmed','PeerConfirmed','UnassignedPerson','PendingPerson','CancelledPerson','PointerWithoutConsent']:
   self.assertIn(name,page)
  self.assertNotIn('DeletedPerson',page)

 def test_staff_create_trainers_and_created_trainer_can_be_selected(self):
  for staff_user,username in [('admin','HLV_Nam'),('letan','hlv_lan')]:
   staff=app.test_client();self.login(staff_user,'Gym@12345',staff)
   self.assertEqual(staff.get('/trainers').status_code,200)
   self.assertIn('Quản lý HLV',staff.get('/').get_data(as_text=True))
   self.assertEqual(staff.post('/trainers',data={}).status_code,400)
   data=dict(full_name='Nguyen Trainer',username=username,password='Trainer12345',confirm_password='Trainer12345',role='admin')
   self.assertEqual(self.post('/trainers',data,staff).status_code,302)
   page=staff.get('/trainers').get_data(as_text=True)
   self.assertIn(username.lower(),page);self.assertNotIn('Trainer12345',page)
   self.assertEqual(self.post('/trainers',data,staff).status_code,200)
   with db() as c:
    u=c.execute('SELECT * FROM users WHERE username=?',(username.lower(),)).fetchone()
    self.assertEqual(u['role'],'trainer');self.assertEqual(u['full_name'],'Nguyen Trainer')
    self.assertTrue(check_password_hash(u['password'],'Trainer12345'));self.assertNotEqual(u['password'],'Trainer12345')
   newtrainer=app.test_client();self.assertEqual(self.login(username,'Trainer12345',newtrainer).status_code,302)
   self.assertEqual(newtrainer.get('/trainer-requests').status_code,200)
   self.assertEqual(newtrainer.get('/trainers').status_code,403)
  self.signup();self.login()
  self.assertIn('Nguyen Trainer',self.c.get('/account').get_data(as_text=True))
  self.assertEqual(self.post('/trainers',dict(username='hacker')).status_code,403)

 def test_trainer_creation_validation_and_no_default_trainer(self):
  with tempfile.TemporaryDirectory() as t:
   original=app.config['DATABASE'];app.config['DATABASE']=str(Path(t)/'fresh.db')
   try:
    init_db()
    with db() as c: self.assertEqual(c.execute("SELECT count(*) FROM users WHERE role='trainer'").fetchone()[0],0)
   finally: app.config['DATABASE']=original
  self.login('letan','Gym@12345')
  base=dict(full_name='Trainer',username='new_hlv',password='Trainer12345',confirm_password='Trainer12345')
  for override in [dict(username='admin'),dict(username='12phone'),dict(username='a'),dict(full_name=''),dict(password='short',confirm_password='short'),dict(confirm_password='different')]:
   self.assertEqual(self.post('/trainers',{**base,**override}).status_code,200)
  with db() as c: self.assertEqual(c.execute("SELECT count(*) FROM users WHERE role='trainer'").fetchone()[0],1)

 def test_admin_and_reception_cannot_schedule_even_after_trainer_accepts(self):
  self.signup();self.login()
  with db() as c:
   mid=c.execute('SELECT id FROM members').fetchone()[0]
   trainer=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
  self.post('/account',dict(action='trainer_request',trainer=trainer))
  with db() as c: rid=c.execute('SELECT id FROM trainer_requests').fetchone()[0]
  hlv=app.test_client();self.login('hlv','Gym@12345',hlv)
  self.post(f'/trainer-requests/{rid}/respond',{'decision':'accept'},hlv)
  data=dict(member=mid,exercise=1,sets=3,reps=15,days=['2'])
  self.assertEqual(self.post('/plans',data,hlv).status_code,302)
  with db() as c: pid=c.execute('SELECT id FROM plans').fetchone()[0]
  for username in ['admin','letan']:
   staff=app.test_client();self.login(username,'Gym@12345',staff)
   self.assertEqual(staff.get('/plans').status_code,403)
   self.assertEqual(self.post('/plans',data,staff).status_code,403)
   self.assertEqual(self.post(f'/plans/{pid}/delete',{},staff).status_code,403)
   page=staff.get('/members').get_data(as_text=True)
   self.assertNotIn('href="/plans',page);self.assertNotIn('>Lập lịch<',page)
  with db() as c: self.assertEqual(c.execute('SELECT count(*) FROM plans').fetchone()[0],1)

 def test_delete_trainer_cancels_links_and_preserves_other_trainers_and_invoices(self):
  self.signup();self.login();member_client=self.c
  self.post('/account',{'package':1})
  with db() as c:
   tid=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
   peer=c.execute("INSERT INTO users(username,password,role,full_name) SELECT 'peer',password,role,'Peer Trainer' FROM users WHERE id=?",(tid,)).lastrowid
  self.post('/account',dict(action='trainer_request',trainer=tid))
  with db() as c: rid=c.execute('SELECT id FROM trainer_requests').fetchone()[0]
  hlv=app.test_client();self.login('hlv','Gym@12345',hlv)
  self.post(f'/trainer-requests/{rid}/respond',{'decision':'accept'},hlv)
  self.post('/plans',dict(member=1,exercise=1,sets=3,reps=15,days=['2']),hlv)
  pending_client=app.test_client()
  self.post('/logout',{});self.signup(phone='0901234568',email='b@example.com');self.login('0901234568',client=pending_client)
  self.post('/account',dict(action='trainer_request',trainer=tid),pending_client)
  self.signup(phone='0901234569',email='c@example.com')
  peer_member=app.test_client();self.login('0901234569',client=peer_member)
  self.post('/account',dict(action='trainer_request',trainer=peer),peer_member)
  with db() as c: peer_rid=c.execute('SELECT max(id) FROM trainer_requests').fetchone()[0]
  peer_client=app.test_client();self.login('peer','Gym@12345',peer_client)
  self.post(f'/trainer-requests/{peer_rid}/respond',{'decision':'accept'},peer_client)
  self.post('/plans',dict(member=3,exercise=2,sets=3,reps=15,days=['3']),peer_client)
  with db() as c: invoices=[tuple(r) for r in c.execute('SELECT * FROM invoices')]
  admin=app.test_client();self.login('admin','Gym@12345',admin)
  url=f'/trainers/{tid}/delete'
  self.assertEqual(admin.get(url).status_code,200)
  self.assertEqual(admin.post(url,data={'confirm':str(tid)}).status_code,400)
  self.post(url,{'confirm':'wrong'},admin)
  with db() as c: self.assertEqual(c.execute('SELECT active FROM users WHERE id=?',(tid,)).fetchone()[0],1)
  self.assertEqual(self.post(url,{'confirm':str(tid)},admin).status_code,302)
  self.assertEqual(hlv.get('/trainer-requests').status_code,302)
  self.assertEqual(self.login('hlv','Gym@12345',hlv).status_code,200)
  with db() as c:
   self.assertEqual(c.execute('SELECT active FROM users WHERE id=?',(tid,)).fetchone()[0],0)
   self.assertIsNone(c.execute('SELECT trainer FROM members WHERE id=1').fetchone()[0])
   self.assertEqual(c.execute("SELECT count(*) FROM trainer_requests WHERE trainer=? AND status='cancelled'",(tid,)).fetchone()[0],2)
   self.assertEqual(c.execute('SELECT active FROM plans WHERE member=1').fetchone()[0],0)
   self.assertEqual(c.execute('SELECT active FROM plans WHERE member=3').fetchone()[0],1)
   self.assertEqual(c.execute('SELECT trainer FROM members WHERE id=3').fetchone()[0],peer)
   self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM invoices')],invoices)
  self.assertEqual(self.post(url,{'confirm':str(tid)},admin).status_code,404)
  self.post('/account',dict(action='trainer_request',trainer=tid),pending_client)
  with db() as c: self.assertEqual(c.execute("SELECT count(*) FROM trainer_requests WHERE trainer=? AND status='pending'",(tid,)).fetchone()[0],0)
  self.post('/account',dict(action='trainer_request',trainer=peer),pending_client)
  with db() as c: self.assertEqual(c.execute("SELECT count(*) FROM trainer_requests WHERE trainer=? AND status='pending'",(peer,)).fetchone()[0],1)
  # Reception can recreate the old login name as a new trainer, then delete that trainer.
  reception=app.test_client();self.login('letan','Gym@12345',reception)
  data=dict(username='hlv',full_name='Replacement Trainer',password='Replacement123',confirm_password='Replacement123')
  self.assertEqual(self.post('/trainers',data,reception).status_code,302)
  with db() as c: new_tid=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
  self.assertNotEqual(new_tid,tid)
  self.assertEqual(self.login('hlv','Replacement123').status_code,302)
  self.assertEqual(self.post(f'/trainers/{new_tid}/delete',{'confirm':str(new_tid)},reception).status_code,302)
  self.assertEqual(peer_client.get('/plans').status_code,200)

 def test_only_staff_can_delete_trainer_and_cannot_delete_non_trainers(self):
  with db() as c:
   tid=c.execute("SELECT id FROM users WHERE username='hlv'").fetchone()[0]
   admin_id=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
   reception_id=c.execute("SELECT id FROM users WHERE username='letan'").fetchone()[0]
  url=f'/trainers/{tid}/delete'
  self.assertEqual(self.c.get(url).status_code,302)
  self.signup();self.login()
  self.assertEqual(self.c.get(url).status_code,403)
  self.assertEqual(self.post(url,{'confirm':str(tid)}).status_code,403)
  self.post('/logout',{});self.login('hlv','Gym@12345')
  self.assertEqual(self.post(url,{'confirm':str(tid)}).status_code,403)
  for staffname in ['admin','letan']:
   staff=app.test_client();self.login(staffname,'Gym@12345',staff)
   for uid in [admin_id,reception_id,99999]:
    self.assertEqual(self.post(f'/trainers/{uid}/delete',{'confirm':str(uid)},staff).status_code,404)
  with db() as c: self.assertEqual(c.execute('SELECT active FROM users WHERE id=?',(tid,)).fetchone()[0],1)

if __name__=='__main__': unittest.main()
