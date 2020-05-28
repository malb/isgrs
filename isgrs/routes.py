# -*- coding: utf-8 -*-
"""

"""
import datetime

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request
from flask_mail import Message
from flask_security import current_user, login_required
from flask_wtf import FlaskForm
from icalendar import Calendar
from icalendar import Event as ICalEvent
from icalendar import vText
import pytz
from sqlalchemy import or_
from wtforms import RadioField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.fields.html5 import DateField, EmailField, URLField
from wtforms.validators import DataRequired

from config import Config

from .email import mkadmininfo, mkannounce, send
from .factory import db
from .models import Event, NoResultFound, User

app = Blueprint("app", __name__)


class UserVisibleError(ValueError):
    """``ValueErrors`` that are user visible."""

    pass


@app.route("/admin", methods=["GET"])
@login_required
def admin():
    all_events = db.session.query(Event).order_by(Event.datetime.desc())
    past_events = all_events.filter(Event.datetime <= datetime.datetime.now())
    future_events = all_events.filter(Event.datetime > datetime.datetime.now())
    return render_template("admin.html", events=future_events, past_events=past_events)


@app.route("/admin/bulk-add", methods=("GET", "POST"))
@login_required
def bulk_add():
    minders = db.session.query(User.email, User.name).filter(User.active).order_by(User.firstname).all()
    minders = minders + [("", "")]
    default_minder = db.session.query(User).filter(User.lead).first()

    class BulkAddForm(FlaskForm):
        startdate = DateField("Start Date", validators=[DataRequired()])
        enddate = DateField("End Date (Inclusive)", validators=[DataRequired()])
        dow = RadioField(
            "Day of Week",
            choices=(("0", "Monday"), ("1", "Tuesday"), ("2", "Wednesday"), ("3", "Thursday"), ("4", "Friday")),
            validators=[DataRequired()],
            default="3",
        )
        time = StringField("Time", validators=[DataRequired()], default="11:00")
        venue = StringField("Venue")
        minder = SelectField("Minder", choices=minders, default=default_minder.email)
        submit = SubmitField("Bulk Add")

    form = BulkAddForm()
    if form.validate_on_submit():
        i = form.startdate.data
        dates = []
        while i.weekday() != int(form.dow.data):
            i += datetime.timedelta(1)
        while i <= form.enddate.data:
            dates.append(i)
            i += datetime.timedelta(7)

        for date in dates:
            time = datetime.time.fromisoformat(form.time.data)
            try:
                minder = db.session.query(User).filter(User.email == form.minder.data).one()
            except NoResultFound:
                minder = None

            dt = datetime.datetime.combine(date, time)
            clash = db.session.query(Event).filter(Event.datetime == dt)
            if clash.count() > 0:
                flash(
                    "Skipping {dt} due to scheduling conflict with {event}".format(
                        dt=dt.strftime("%a, %d %b %Y %H:%M"), event=clash.one()
                    ),
                    category="warning",
                )
                continue

            event = Event(
                datetime=dt,
                venue=form.venue.data,
                minder_firstname=minder.firstname if minder else None,
                minder_lastname=minder.lastname if minder else None,
                minder_email=minder.email if minder else None,
                status="FREE",
            )
            db.session.add(event)
        db.session.commit()

        flash("All done.", category="success")
        return redirect("/admin")

    return render_template("bulk-add.html", form=form)


@app.route("/admin/add", methods=("GET", "POST"))
@login_required
def add():
    event = Event(status="PUBLIC")
    db.session.add(event)
    db.session.commit()
    return redirect("/admin/edit/{event.id}".format(event=event))


@app.route("/admin/edit/<eventid>", methods=("GET", "POST"))
@login_required
def edit(eventid):
    class EditForm(FlaskForm):
        date = DateField("Date", validators=[DataRequired()])
        time = StringField("Time", validators=[DataRequired()])
        title = StringField("Seminar Title")
        abstract = TextAreaField("Abstract")
        speaker_firstname = StringField("Firstname")
        speaker_lastname = StringField("Lastname")
        speaker_email = EmailField("E-Mail")
        speaker_link = URLField("Link")
        speaker_affiliation = StringField("Affiliation")
        speaker_bio = TextAreaField("Bio")
        minder_firstname = StringField("Firstname")
        minder_lastname = StringField("Lastname")
        minder_email = EmailField("E-Mail")
        venue = StringField("Venue")
        status = SelectField(
            "Status",
            choices=(("PUBLIC", "PUBLIC"), ("PRIVATE", "PRIVATE"), ("PLACEHOLDER", "PLACEHOLDER"), ("FREE", "FREE")),
        )
        public_notes = TextAreaField("Public Notes")
        private_notes = TextAreaField("Internal Notes")
        submit = SubmitField("Save")

    eventid = int(eventid)

    try:
        event = Event.by_id(eventid)
    except NoResultFound:
        msg = "Event <{eventid}> not found.".format(eventid=eventid)
        return render_template("error.html", msg=msg)

    form = EditForm(obj=event)

    if form.validate_on_submit():
        conflict = Event.conflict(form.date.data, form.time.data, event.id)
        if conflict is not None:
            flash("Scheduling clash with {event}".format(event=conflict), category="danger")
            return redirect("/admin/edit/{event.id}".format(event=event))

        event.set_date_time(form.date.data, form.time.data)

        form.populate_obj(event)

        if (
            event.title or event.speaker_email or event.speaker_firstname or event.speaker_lastname
        ) and event.status == "FREE":
            flash(
                "Setting status of {event} to PLACEHOLDER since details were filled in.".format(event=event),
                category="warning",
            )
            event.status = "PLACEHOLDER"

        db.session.commit()
        return redirect("/admin")
    else:
        if event.datetime is not None:
            form.date.data = event.datetime.date()
            form.time.data = event.datetime.time().strftime("%H:%M")

    return render_template("edit.html", form=form, event=event)


@app.route("/admin/delete/<eventid>", methods=("POST",))
@login_required
def delete(eventid):
    try:
        event = Event.by_id(eventid)
    except NoResultFound:
        msg = "Event <{eventid}> not found.".format(eventid=eventid)
        return render_template("error.html", msg=msg)

    db.session.delete(event)
    db.session.commit()
    flash("Seminar {event} deleted.".format(event=event), category="success")
    return redirect("/admin")


@app.route("/admin/documentation", methods=["GET"])
@login_required
def admin_documentation():
    raw = request.args.get("raw")

    active_users = User.query.filter(User.active).all()
    markdown = render_template("admin-documentation.md", active_users=active_users)
    if raw:
        return Response(markdown, mimetype="text/plain")
    else:
        return render_template("markdown.html", title="Documentation", markdown=markdown)


def _announce(eventid, sender):
    if eventid == "next":
        event = (
            db.session.query(Event)
            .filter(Event.datetime > datetime.datetime.now())
            .filter(or_(Event.status == "PUBLIC", Event.status == "PRIVATE"))
            .order_by(Event.datetime.asc())
            .first()
        )
        if event is None:
            raise UserVisibleError("There is no upcoming seminar.")

        if event.datetime - datetime.datetime.now() > datetime.timedelta(30):
            raise UserVisibleError("Upcoming seminar is more than 30 days in the future.")

    else:
        eventid = int(eventid)
        try:
            event = Event.by_id(eventid)
        except NoResultFound:
            msg = "Seminar <{eventid}> not found.".format(eventid=eventid)
            raise UserVisibleError(msg)

    send(mkannounce(event, sender))
    return event


@app.route("/admin/announce/<token>/<eventid>", methods=("GET",))
@login_required
def announce(token, eventid):
    if token != current_user.announce_token:
        flash("Wrong token.", category="danger")
        return redirect("/admin")

    try:
        event = _announce(eventid, sender=current_user)
    except UserVisibleError as e:
        flash(str(e), category="danger")
        return redirect("/admin")

    flash("Announcement for {event} sent.".format(event=event), category="success")
    return redirect("/admin")


@app.route("/json/admin/announce/<token>/<eventid>", methods=("GET",))
def json_announce(token, eventid):
    for user in db.session.query(User).all():
        if token == user.announce_token:
            break
    else:
        return jsonify(success=False, message="Wrong token.")

    try:
        _announce(eventid, sender=user)
    except UserVisibleError as e:
        return jsonify(success=False, message=str(e))

    return jsonify(success=True)


@app.route("/speaker-edit/<token>/<eventid>", methods=("GET", "POST"))
def speaker_edit(token, eventid):
    class SpeakerEditForm(FlaskForm):
        speaker_firstname = StringField("Firstname", validators=[DataRequired()])
        speaker_lastname = StringField("Lastname", validators=[DataRequired()])
        speaker_link = StringField("URL")
        speaker_affiliation = StringField("Affiliation")
        speaker_bio = TextAreaField("Bio", validators=[DataRequired()])
        title = StringField("Title", validators=[DataRequired()])
        abstract = TextAreaField("Abstract", validators=[DataRequired()])
        submit = SubmitField("Save")

    eventid = int(eventid)
    try:
        event = Event.by_id(eventid)
    except NoResultFound:
        msg = "Event <{eventid}> not found.".format(eventid=eventid)
        return render_template("error.html", msg=msg)

    if token != event.token:
        msg = "Wrong token."
        return render_template("error.html", msg=msg)

    form = SpeakerEditForm(obj=event)
    if form.validate_on_submit():
        form.populate_obj(event)
        db.session.commit()
        flash("All done, thank you.", category="success")
        send(mkadmininfo(event))
        return redirect("/")

    return render_template("speaker-edit.html", form=form, event=event)


@app.route("/admin/request-speaker-edit/<eventid>", methods=("GET", "POST"))
@login_required
def request_speaker_edit(eventid):
    try:
        event = Event.by_id(eventid)
    except NoResultFound:
        flash("Event <{eventid}> not found.".format(eventid=eventid), category="warning")
        return redirect("/admin")

    admins = db.session.query(User.email).filter(User.active).all()
    admins = [admin[0] for admin in admins]

    class SolicitSpeakerEditForm(FlaskForm):
        subject = StringField("Subject:", validators=[DataRequired()])
        message = TextAreaField("Mail", validators=[DataRequired()])
        cc = StringField("Cc:")
        submit = SubmitField("Send")

    form = SolicitSpeakerEditForm()
    if form.validate_on_submit():
        to = "{event.speaker_firstname} {event.speaker_lastname} <{event.speaker_email}>".format(event=event)
        msg = Message(form.subject.data, recipients=[to], cc=admins, sender=current_user.email)
        msg.body = form.message.data
        send(msg)
        flash("Message sent.", category="success")
        return redirect("/admin")
    else:
        form.subject.data = "ISG Research Seminar on {event.datetime_str}".format(event=event)
        form.cc.data = ", ".join(admins)
        form.message.data = render_template("request-speaker-edit.md", event=event, sender=current_user)
    return render_template("request-speaker-edit.html", form=form, event=event)


#
# Public Routes
#


@app.route("/", methods=["GET"])
def index():
    free = request.args.get("free")
    events = (db.session.query(Event)
              .filter(Event.datetime != None)  ## we might create "temp" entries with no datetime
              .order_by(Event.datetime.desc())
              .all())

    next_event = (
        db.session.query(Event)
        .filter(Event.datetime > datetime.datetime.now() - datetime.timedelta(hours=1))
        .filter(Event.status == "PUBLIC")
        .order_by(Event.datetime.asc())
        .first()
    )
    if next_event and next_event.datetime - datetime.datetime.now() > datetime.timedelta(30):
        next_event = None

    return render_template("index.html", events=events, free=free, single=False, next_event=next_event)


@app.route("/d/<date>", methods=["GET"])
def day(date):
    free = request.args.get("free")
    try:
        start = datetime.datetime.fromisoformat(date)
        end = start + datetime.timedelta(1)
    except ValueError:
        return render_template("error.html", "Cannot parse date format")
    events = (
        db.session.query(Event)
        .filter(Event.datetime >= start)
        .filter(Event.datetime < end)
        .order_by(Event.datetime.desc())
        .all()
    )
    return render_template("index.html", events=events, free=free, single=True)


@app.route("/ical", methods=["GET"])
def ical():
    """
    Publish icalendar of public seminars.

    """

    free = request.args.get("free")
    events = (db.session.query(Event)
              .filter(Event.datetime != None)  ## we might create "temp" entries with no datetime
              .order_by(Event.datetime.desc()))

    if free != "shown":
        events = events.filter(or_(Event.status == "PUBLIC", Event.status == "PLACEHOLDER"))
    else:
        events = events.filter(or_(Event.status == "PUBLIC", Event.status == "PLACEHOLDER", Event.status == "FREE"))
    events = events.all()

    cal = Calendar()
    cal.add("prodid", "-//ISG Research Seminars//{url}//".format(url=Config.FRONTEND_DOMAIN))
    cal.add("version", "2.0")
    for event in events:
        icalevent = ICalEvent()
        if event.status == "PUBLIC":
            icalevent.add("summary", "{event.title} by {event.speaker}".format(event=event))
        elif event.status == "PLACEHOLDER":
            icalevent.add("summary", "TBC")
        elif event.status == "FREE":
            icalevent.add("summary", "Free Slot")
        else:
            raise ValueError("This shouldn't happen.")

        icalevent.add("description", event.public_notes + "\n\n" + event.abstract + "\n\n" + event.speaker_bio)
        start = event.datetime.replace(tzinfo=pytz.timezone("Europe/London"))
        icalevent.add("dtstart", start)
        icalevent.add("dtend", start + datetime.timedelta(hours=1))
        icalevent.add("dtstamp", datetime.datetime.now())
        icalevent["location"] = vText(
            "{event.venue}, Royal Holloway, University of London, Egham, Surrey, UK".format(event=event)
        )
        icalevent["uid"] = event.datetime.strftime("%Y%m%d%H%M@{url}".format(url=Config.FRONTEND_DOMAIN))
        cal.add_component(icalevent)
    return Response(cal.to_ical(), mimetype="text/calendar")


@app.route("/information-for-speakers", methods=["GET"])
def information_for_speakers():
    raw = request.args.get("raw")

    markdown = render_template("information-for-speakers.md")
    if raw:
        return Response(markdown, mimetype="text/plain")
    else:
        return render_template("markdown.html", title="Information for Speakers", markdown=markdown)
