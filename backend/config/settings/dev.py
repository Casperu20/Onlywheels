from .base import *  # noqa: F403
from .base import env

DEBUG = True
AUTH_COOKIE_SECURE = False
SMARTBILL_DEMO = env.bool("SMARTBILL_DEMO", default=True)
