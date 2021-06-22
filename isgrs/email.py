from flask_mail import Message
from flask import render_template
from config import Config
from config import logging
from .factory import mail, db
from .models import User


def mkmsg(subject, to, cc, frm, template, **kwds):
    msg = Message(subject, sender=frm, recipients=to, cc=cc)
    msg.body = render_template(template, **kwds)
    return msg


def mkannounce(event, sender, signers=None):
    if signers is None:
        signers = db.session.query(User.firstname).filter(User.active).all()
        signers = ", ".join([sender[0] for sender in signers])

    if event.status == "PUBLIC":
        to = Config.ANNOUNCE_PUBLIC
    else:
        to = []

    return mkmsg(
        "{event.datetime_str} in {event.venue}: {event.speaker}".format(event=event),
        to=to,
        cc=Config.ANNOUNCE_INTERNAL,
        frm=sender.email,
        template="announce-email.md",
        event=event,
        signers=signers,
    )


def mkadmininfo(event):
    admins = db.session.query(User.email).filter(User.active).all()
    admins = [admin[0] for admin in admins]

    if event.minder_email not in admins:
        cc = [event.minder_email]
    else:
        cc = []

    return mkmsg(
        "[{title}] update to {event.datetime_str}".format(event=event, title=Config.TITLE),
        to=admins,
        cc=cc,
        frm=admins[0],
        template="admin-info.md",
        event=event,
    )


def send(msg):
    if Config.TESTING:
        logger = logging.getLogger("email")
        for line in str(msg).splitlines():
            logger.info(line)
    else:
        mail.send(msg)
