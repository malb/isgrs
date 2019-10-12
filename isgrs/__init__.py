# -*- coding: utf-8 -*-
from .factory import create_app  # noqa
from .factory import db, migrate, mail  # noqa
from . import routes, models  # noqa

import logging

logging.getLogger("email").setLevel(logging.INFO)
