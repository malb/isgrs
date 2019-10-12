#!/usr/bin/env python
# -*- coding: utf-8 -*-

from isgrs.factory import create_app, db, make_session  # noqa
from isgrs.models import Event, User  # noqa
import datetime  # noqa

session = make_session()  # noqa
app = create_app()
app.app_context().push()
