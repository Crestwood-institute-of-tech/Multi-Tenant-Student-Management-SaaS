from .development import *  # noqa: F403

DEBUG = True
SECRET_KEY = "test-only-not-for-deployment"
ALLOWED_HOSTS = ["localhost", "testserver"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
