import tempfile, unittest, sqlite3
from pathlib import Path
from unittest.mock import patch
from werkzeug.security import check_password_hash
from index import app, init_db, db, confirmation as real_confirmation

class MemberFlow(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  app.config.update(TESTING=True,DATABASE=str(Path(self.tmp.name)/'test.db'))
  init_db(); self.c=app.test_client()
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
  staff=app.test_client();self.login('thungan','Gym@12345',staff)
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
  for path in ['/','/members','/payments','/plans','/settings','/register']:
   self.assertEqual(self.c.get(path).status_code,200)
  self.assertEqual(self.c.get('/account').status_code,403)

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
  for user in ['hlv','thungan']:
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

if __name__=='__main__': unittest.main()
