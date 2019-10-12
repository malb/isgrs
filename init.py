#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Direct Python access to database
"""
from isgrs.factory import make_session, create_app, db, create_user

session = make_session()  # noqa
app = create_app()
app.app_context().push()

db.create_all()

# create_user(
#     app,
#     firstname="Alice",
#     lastname="Bob",
#     email="alice@bob.com",
#     password="password",
# )

# e = Event(datetime=datetime(2020, 5, 1, 11, 00),
#           title="An interesting talk",
#           abstract="It is about interesting stuff!",
#           speaker_firstname="Interesting",
#           speaker_lastname="Speaker",
#           speaker_email="speaker@email.com",
#           speaker_bio="Has done stuff!",
#           minder_firstname="Mallory",
#           minder_lastname="Eve",
#           minder_email="mallory@eve.com",
#           venue="Venue!!!",
#           status="PUBLIC")
# db.session.add(e)

db.session.commit()
