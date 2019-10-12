# -*- coding: utf-8 -*-
from isgrs import create_app  # noqa
import logging

app = create_app()

console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(name)s: %(message)s"))
logging.getLogger("email").addHandler(console)
