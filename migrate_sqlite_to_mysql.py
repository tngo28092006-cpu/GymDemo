"""One-time copy into an EMPTY MySQL database; never deletes the SQLite source."""
import argparse
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from mysql_backend import Connection, initialize

TABLES = ['users','packages','members','exercises','invoices','plans','settings',
          'trainer_requests','notifications','staff_notifications','app_migrations']


def migrate(source_path, config):
    source = sqlite3.connect(Path(source_path).resolve().as_uri()+'?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    try:
        initialize(config)
        with Connection(config) as target:
            target.execute('BEGIN IMMEDIATE')
            for table in TABLES:
                if table!='settings' and target.execute(f'SELECT count(*) FROM `{table}`').fetchone()[0]:
                    raise ValueError('MySQL target is not empty. Use a NEW database before running the app.')
            available={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'users','members','packages'} <= available:
                raise ValueError('Source is not a Gym database')
            counts={}
            for table in TABLES:
                if table not in available: continue
                allowed={r['Field'] for r in target.execute(f'SHOW COLUMNS FROM `{table}`') if 'GENERATED' not in r['Extra']}
                columns=[r['name'] for r in source.execute(f'PRAGMA table_info({table})') if r['name'] in allowed]
                names=','.join('`'+column+'`' for column in columns)
                placeholders=','.join('?' for _ in columns)
                rows=source.execute(f'SELECT {names} FROM "{table}" ORDER BY '+('name' if table=='app_migrations' else 'id')).fetchall()
                if table=='settings':
                    for row in rows: target.execute('UPDATE settings SET max_days=? WHERE id=1',(row['max_days'],))
                elif rows:
                    target.executemany(f'INSERT INTO `{table}`({names}) VALUES({placeholders})',[tuple(row) for row in rows])
                counts[table]=len(rows)
            return counts
    finally:
        source.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default=str(Path(__file__).with_name('gym.db')))
    args=parser.parse_args()
    load_dotenv(Path(__file__).with_name('.env'),override=False)
    config=dict(host=os.getenv('MYSQL_HOST','127.0.0.1'),port=int(os.getenv('MYSQL_PORT','3306')),
                user=os.getenv('MYSQL_USER','root'),password=os.getenv('MYSQL_PASSWORD',''),
                database=os.getenv('MYSQL_DATABASE','gym_demo'))
    try:
        counts=migrate(args.source,config)
        print('Copied successfully:',counts)
        print('SQLite source was left unchanged. You can now start Flask.')
    except Exception as error:
        raise SystemExit('Migration failed; source unchanged. '+str(error)) from error
