# -*- coding: utf-8 -*-
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_security import Security, SQLAlchemyUserDatastore
from upstream.markdown import Markdown
from flask_security.utils import encrypt_password

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
bootstrap = Bootstrap()
security = Security()
markdown = Markdown(None)


def make_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from config import Config

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


def create_app():
    from config import Config
    from isgrs.routes import app as blueprint
    from .models import User, Role

    app = Flask(
        __name__, template_folder=Config.TEMPLATE_DIR, static_folder=Config.STATIC_DIR
    )
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    bootstrap.init_app(app)
    markdown.init_app(app)

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security.init_app(app, user_datastore)

    app.register_blueprint(blueprint)
    return app


def create_user(app, firstname, lastname, email, password, lead=False, commit=True):
    from .models import User

    security = app.extensions["security"]
    security.datastore.create_user(
        firstname=firstname,
        lastname=lastname,
        email=email,
        password=encrypt_password(password),
        lead=lead,
    )
    db = app.extensions["sqlalchemy"].db
    if commit:
        db.session.commit()
    return db.session.query(User).filter(User.email == email).one()
