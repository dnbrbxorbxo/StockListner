import os
from datetime import datetime

from peewee import SqliteDatabase, Model, CharField, DateField, DateTimeField

# Connect to a SQLite database
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stocks.db')
db = SqliteDatabase(db_path , pragmas={'journal_mode': 'wal', 'cache_size': -1024 * 64})

class Stock(Model):
    basDt = DateField()
    srtnCd = CharField()
    isinCd = CharField()
    mrktCtg = CharField()
    itmsNm = CharField()
    crno = CharField()
    corpNm = CharField()

    db1 = CharField()
    db2 = CharField()
    db3 = CharField()
    db4 = CharField()
    db5 = CharField()
    db6 = CharField()
    db7 = CharField()
    db8 = CharField()
    db9 = CharField()
    db10 = CharField()
    db11 = CharField()

    updatedAt = DateTimeField(default=datetime.now)

    class Meta:
        database = db

# Create the table
db.connect()
db.create_tables([Stock])
