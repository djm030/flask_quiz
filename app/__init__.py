from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask.cli import with_appcontext
import os
import click
from .database import db
from .models import Question  # Question 모델 임포트

def create_app():
    app = Flask(__name__)

    # 데이터베이스 파일 경로 설정 및 앱 설정
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    dbfile = os.path.join(basedir, 'db.sqlite')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + dbfile
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 데이터베이스 및 마이그레이션 초기화
    db.init_app(app)
    migrate = Migrate(app, db)

    # 라우트(블루프린트) 등록
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # 초기화 명령어 정의
    def add_initial_questions():
        initial_questions = [
            "오즈코딩스쿨에 대해서 알고 계신가요?",
            "프론트엔드 과정에 참여하고 계신가요?",
            "전공자 이신가요?",
            "프로젝트를 진행해보신적 있으신가요?",
            "개발자로 일한 경력이 있으신가요?",
        ]

        for question_content in initial_questions:
            existing_question = Question.query.filter_by(content=question_content).first()
            if not existing_question:
                new_question = Question(content=question_content)
                db.session.add(new_question)
        db.session.commit()

    @click.command('init-db')
    @with_appcontext
    def init_db_command():
        db.create_all()
        add_initial_questions()
        click.echo('Initialized the database.')

    app.cli.add_command(init_db_command)

    return app