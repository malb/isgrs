# -*- coding: utf-8 -*-

import datetime
import hashlib
import uuid

from flask_security import RoleMixin, UserMixin
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import NoResultFound

from config import Config
from isgrs.factory import db


class Event(db.Model):

    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime(timezone=True), unique=True)
    title = db.Column(db.String, default="")
    abstract = db.Column(db.Text, default="")
    speaker_firstname = db.Column(db.String, default="")
    speaker_lastname = db.Column(db.String, default="")
    speaker_affiliation = db.Column(db.String, default="")
    speaker_email = db.Column(db.String, default="")
    speaker_link = db.Column(db.String, default="")
    speaker_bio = db.Column(db.Text, default="")
    minder_firstname = db.Column(db.String, default="")
    minder_lastname = db.Column(db.String, default="")
    minder_email = db.Column(db.String, default="")
    venue = db.Column(db.String, default="")
    status = db.Column(
        db.Enum("PUBLIC", "PRIVATE", "PLACEHOLDER", "FREE"), default="FREE"
    )
    public_notes = db.Column(db.Text, default="")
    private_notes = db.Column(db.Text, default="")

    def __init__(self, **kwds):
        default_minder = db.session.query(User).filter(User.lead).first()

        self.datetime = kwds.get("datetime", None)
        self.title = kwds.get("title", "")
        self.abstract = kwds.get("abstract", "")
        self.speaker_firstname = kwds.get("speaker_firstname", "")
        self.speaker_lastname = kwds.get("speaker_lastname", "")
        self.speaker_affiliation = kwds.get("speaker_affiliation", "")
        self.speaker_email = kwds.get("speaker_email", "")
        self.speaker_link = kwds.get("speaker_link", "")
        self.speaker_bio = kwds.get("speaker_bio", "")
        self.minder_firstname = kwds.get("minder_firstname", default_minder.firstname)
        self.minder_lastname = kwds.get("minder_lastname", default_minder.lastname)
        self.minder_email = kwds.get("minder_email", default_minder.email)
        self.venue = kwds.get("venue", "")
        self.status = kwds.get(
            "status", "FREE" if not self.speaker_lastname else "PUBLIC"
        )
        self.public_notes = kwds.get("public_notes", "")
        self.private_notes = kwds.get("private_notes", "")

    @staticmethod
    def by_id(eventid):
        event = Event.query.get(eventid)
        if event is None:
            raise NoResultFound
        else:
            return event

    @property
    def token(self):
        return hashlib.sha256(
            (Config.SECRET_KEY + "!" + "event" + str(self.id) + "!").encode()
        ).hexdigest()

    @property
    def datetime_str(self):
        return self.datetime.strftime("%a, %d %b %Y %H:%M")

    @property
    def speaker(self):
        speaker = self.speaker_firstname + " " + self.speaker_lastname
        if speaker != " ":
            return speaker
        else:
            return "TBC"

    def __repr__(self):
        return "<{datetime}: {speaker}>".format(
            datetime=self.datetime_str, speaker=self.speaker
        )

    @property
    def speaker_edit_url(self):
        return "{frontend_domain}/speaker-edit/{event.token}/{event.id}".format(
            frontend_domain=Config.FRONTEND_DOMAIN, event=self
        )

    @property
    def in_future(self):
        return self.datetime > datetime.datetime.now()

    def conflict(self):
        """
        Return event (if any) in the db that conflicts with this event by having the same datetime.

        """
        clash = (
            db.session.query(Event)
            .filter(Event.datetime == self.datetime)
            .filter(Event.id != self.id)
        )
        if clash.count() > 0:
            return clash.one()
        else:
            return None

    def set_date_time(self, date, time):
        if not isinstance(date, datetime.date):
            date = datetime.date.fromisoformat(date)
        if not isinstance(time, datetime.time):
            time = datetime.time.fromisoformat(time)
        self.datetime = datetime.datetime.combine(date, time)


class RolesUsers(db.Model):
    __tablename__ = "roles_users"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))


class Role(db.Model, RoleMixin):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    description = db.Column(db.String)


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String)
    lastname = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String, unique=True)
    announce_token = db.Column(db.String, unique=True)
    active = db.Column(db.Boolean)
    lead = db.Column(db.Boolean)
    roles = db.relationship(
        "Role", secondary="roles_users", backref=db.backref("users", lazy="dynamic")
    )

    def __init__(self, **kwds):
        self.firstname = kwds["firstname"]
        self.lastname = kwds["lastname"]
        self.email = kwds["email"]
        self.password = kwds["password"]
        self.announce_token = kwds.get("announce_token", str(uuid.uuid4()))
        self.active = kwds.get("active", True)
        self.lead = kwds.get("lead", False)
        self.roles = kwds.get("roles", None)

    @hybrid_property
    def name(self):
        return self.firstname + " " + self.lastname
