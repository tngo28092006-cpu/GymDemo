"""MySQL connections with the small execute/fetch interface used by the app."""
import hashlib
import re
from datetime import date, datetime
from pathlib import Path

import pymysql
from pymysql.constants import CLIENT


class Row(tuple):
    def __new__(cls, values, columns):
        values = tuple(v.isoformat() if isinstance(v, (date, datetime)) else v for v in values)
        obj = super().__new__(cls, values)
        obj.columns = tuple(columns)
        return obj

    def __getitem__(self, key):
        return super().__getitem__(self.columns.index(key) if isinstance(key, str) else key)

    def keys(self):
        return self.columns


class Result:
    def __init__(self, cursor):
        self.lastrowid = cursor.lastrowid
        self.rowcount = cursor.rowcount
        columns = [d[0] for d in cursor.description] if cursor.description else []
        self.rows = iter([Row(row, columns) for row in cursor.fetchall()] if columns else [])
        cursor.close()

    def fetchone(self):
        return next(self.rows, None)

    def fetchall(self):
        return list(self.rows)

    def __iter__(self):
        return self.rows


def translate(sql):
    # Translate only placeholders outside SQL literals; values always stay bound.
    sql = re.sub(r'\bINSERT\s+OR\s+IGNORE\b', 'INSERT IGNORE', sql, flags=re.I)
    output = []; quote = None; i = 0
    while i < len(sql):
        char = sql[i]
        if quote:
            output.append(char)
            if char == '\\' and i + 1 < len(sql):
                i += 1; output.append(sql[i])
            elif char == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    i += 1; output.append(sql[i])
                else:
                    quote = None
        elif char in "'\"`":
            quote = char; output.append(char)
        else:
            output.append('%s' if char == '?' else char)
        i += 1
    return ''.join(output)


class Connection:
    def __init__(self, config):
        self.raw = pymysql.connect(**config, charset='utf8mb4', autocommit=False,
                                   client_flag=CLIENT.FOUND_ROWS, connect_timeout=10)
        self.lock_name = 'gym-write-' + hashlib.sha256(config['database'].encode()).hexdigest()[:40]
        self.locked = False

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        try:
            self.rollback() if kind else self.commit()
        finally:
            self.raw.close()

    def execute(self, sql, params=()):
        if sql.strip().upper() == 'BEGIN IMMEDIATE':
            if not self.locked:
                with self.raw.cursor() as cursor:
                    cursor.execute('SELECT GET_LOCK(%s, 10)', (self.lock_name,))
                    if cursor.fetchone()[0] != 1:
                        raise pymysql.OperationalError(1205, 'Gym transaction lock timed out; retry the request')
                self.locked = True
                self.raw.begin()
            return self.execute('SELECT 1')
        cursor = self.raw.cursor()
        try:
            cursor.execute(translate(sql), params or None)
            return Result(cursor)
        except BaseException:
            cursor.close()
            raise

    def executemany(self, sql, params):
        cursor = self.raw.cursor()
        try:
            cursor.executemany(translate(sql), params)
            return Result(cursor)
        except BaseException:
            cursor.close()
            raise

    def release(self):
        if self.locked:
            with self.raw.cursor() as cursor:
                cursor.execute('SELECT RELEASE_LOCK(%s)', (self.lock_name,))
            self.locked = False

    def commit(self):
        self.raw.commit()
        self.release()

    def rollback(self):
        self.raw.rollback()
        self.release()


def initialize(config):
    # Schema is created separately with CREATE DATABASE; no elevated runtime permissions needed.
    with Connection(config) as connection:
        schema = Path(__file__).with_name('schema_mysql.sql').read_text(encoding='utf-8')
        for statement in schema.split(';'):
            if statement.strip():
                connection.execute(statement)
