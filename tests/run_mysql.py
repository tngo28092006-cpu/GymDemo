"""Run the application flow suite against a disposable real MySQL database per test.
MYSQL_TEST_USER needs CREATE/DROP DATABASE on gym_test_* only. Never use production credentials.
"""
import os
import secrets
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
# Bootstrap the existing migration tests on SQLite; actual flows below use MySQL.
os.environ['DB_BACKEND']='sqlite'
import pymysql
from werkzeug.security import generate_password_hash
from test_members import MemberFlow
from index import app,init_db,db


class MySQLFlow(MemberFlow):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.database='gym_test_'+secrets.token_hex(8)
        self.connection_args=dict(host=os.getenv('MYSQL_TEST_HOST','127.0.0.1'),
                                  port=int(os.getenv('MYSQL_TEST_PORT','3306')),
                                  user=os.getenv('MYSQL_TEST_USER','root'),
                                  password=os.getenv('MYSQL_TEST_PASSWORD',''))
        with pymysql.connect(**self.connection_args,autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute('CREATE DATABASE `'+self.database+'` CHARACTER SET utf8mb4')
        app.config.update(TESTING=True,DB_BACKEND='mysql',MYSQL={**self.connection_args,'database':self.database})
        init_db()
        with db() as c:
            self.assertEqual(c.execute("SELECT count(*) FROM users WHERE role='trainer'").fetchone()[0],0)
        with db() as c:
            c.execute("INSERT INTO users(username,password,role) VALUES(?,?,'trainer')",('hlv',generate_password_hash('Gym@12345')))
        self.c=app.test_client()
        self.mail=patch('index.confirmation',return_value='SMTP test');self.send=self.mail.start()

    def tearDown(self):
        self.mail.stop()
        with pymysql.connect(**self.connection_args,autocommit=True) as connection:
            with connection.cursor() as cursor:cursor.execute('DROP DATABASE `'+self.database+'`')
        app.config['DB_BACKEND']='sqlite'
        self.tmp.cleanup()

    def test_sqlite_copy_preserves_login_history_and_refuses_nonempty_target(self):
        import hashlib
        from migrate_sqlite_to_mysql import migrate
        original_mysql=app.config['MYSQL']
        target_name=self.database+'_copy'
        source=Path(self.tmp.name)/'legacy.db'
        with pymysql.connect(**self.connection_args,autocommit=True) as connection:
            with connection.cursor() as cursor:cursor.execute('CREATE DATABASE `'+target_name+'` CHARACTER SET utf8mb4')
        try:
            app.config.update(DB_BACKEND='sqlite',DATABASE=str(source))
            init_db()
            with db() as c:
                uid=c.execute("INSERT INTO users(username,password,role) VALUES('old-member',?,'member')",(generate_password_hash('Member12345'),)).lastrowid
                mid=c.execute("INSERT INTO members(name,phone,email,registered,user_id) VALUES('Thắng','0901234567','member@example.com','2026-10-01',?)",(uid,)).lastrowid
                c.execute("INSERT INTO invoices(member,months,amount,created,paid_at,starts,expires) VALUES(?,1,500000,'2026-10-01','2026-10-01','2026-10-01','2026-11-01')",(mid,))
                c.execute("INSERT INTO plans(member,exercise,sets,reps,days) VALUES(?,1,3,15,'2')",(mid,))
                c.execute("INSERT INTO notifications(member,message,link,created) VALUES(?,'Đăng ký thành công','/account','2026-10-01T09:00:00')",(mid,))
            before=hashlib.sha256(source.read_bytes()).hexdigest()
            config={**self.connection_args,'database':target_name}
            counts=migrate(source,config)
            self.assertEqual(counts['members'],1)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
            app.config.update(DB_BACKEND='mysql',MYSQL=config)
            self.assertEqual(self.login().status_code,302)
            with db() as c:
                self.assertEqual(c.execute('SELECT amount FROM invoices').fetchone()[0],500000)
                self.assertEqual(c.execute('SELECT count(*) FROM plans').fetchone()[0],1)
                self.assertEqual(c.execute('SELECT message FROM notifications').fetchone()[0],'Đăng ký thành công')
            with self.assertRaises(ValueError):migrate(source,config)
        finally:
            app.config.update(DB_BACKEND='mysql',MYSQL=original_mysql)
            with pymysql.connect(**self.connection_args,autocommit=True) as connection:
                with connection.cursor() as cursor:cursor.execute('DROP DATABASE `'+target_name+'`')

    @unittest.skip('SQLite legacy schema migration is covered by the SQLite suite')
    def test_existing_data_migration(self):
        pass


if __name__=='__main__':
    suite=(unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:],module=sys.modules[__name__])
           if len(sys.argv)>1 else unittest.defaultTestLoader.loadTestsFromTestCase(MySQLFlow))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
