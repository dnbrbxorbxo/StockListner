from peewee import *

# SQLite 데이터베이스 연결
db = SqliteDatabase('MathBank.db')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    name = CharField()
    grade = IntegerField()
    parent_contact = CharField()
    user_class = CharField()
    school = CharField()
    username = CharField(unique=True)
    password = CharField()
    approved = BooleanField(default=True)


class Paper(BaseModel):
    category = BooleanField(default=True)
    title = CharField()
    description = TextField()
    difficulty = IntegerField()
    question_type = CharField()  # 'objective' or 'subjective'
    options = TextField(null=True)  # JSON string to store multiple choice options
    correct_answer = CharField()
    answer = TextField(null=True)  # Answer to the question
    solution = TextField()
    explanation_pdf = CharField(null=True)
    explanation_image = CharField(null=True)
    explanation_video_link = CharField(null=True)
    parent = ForeignKeyField('self', null=True, backref='children')

# 데이터베이스 초기화
db.connect()

# 기존 테이블을 삭제합니다. (안전하게 사용하려면 주석 처리)
db.drop_tables([User, Paper], safe=True)

# 새 테이블을 생성합니다.
db.create_tables([User, Paper], safe=True)
