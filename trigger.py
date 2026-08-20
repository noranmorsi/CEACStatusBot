import os

from dotenv import load_dotenv

from CEACStatusBot import (
    EmailNotificationHandle,
    NotificationManager,
)


# ------------------------------------------------------------
# Load .env if present
# ------------------------------------------------------------

if os.path.exists(".env"):
    load_dotenv(dotenv_path=".env")
else:
    print(".env not found, using system environment only")


# ------------------------------------------------------------
# Required CEAC environment variables
# ------------------------------------------------------------

try:
    LOCATION = os.environ["LOCATION"]
    NUMBER = os.environ["NUMBER"]
    PASSPORT_NUMBER = os.environ["PASSPORT_NUMBER"]
    SURNAME = os.environ["SURNAME"]

except KeyError as e:
    raise RuntimeError(
        f"Missing required environment variable: {e}"
    ) from e


# ------------------------------------------------------------
# Create notification manager
# ------------------------------------------------------------

notificationManager = NotificationManager(
    LOCATION,
    NUMBER,
    PASSPORT_NUMBER,
    SURNAME,
)


# ------------------------------------------------------------
# Email notifications
# ------------------------------------------------------------

FROM = os.getenv("FROM")
TO = os.getenv("TO")
PASSWORD = os.getenv("PASSWORD")
SMTP = os.getenv("SMTP", "")

if FROM and TO and PASSWORD:
    emailNotificationHandle = EmailNotificationHandle(
        FROM,
        TO,
        PASSWORD,
        SMTP,
    )

    notificationManager.addHandle(
        emailNotificationHandle
    )
else:
    print(
        "Email notification config missing or incomplete"
    )


# ------------------------------------------------------------
# Daily update mode
# ------------------------------------------------------------

FORCE_DAILY_UPDATE = (
    os.getenv(
        "FORCE_DAILY_UPDATE",
        "",
    ).lower()
    == "true"
)


# ------------------------------------------------------------
# Run CEAC status check
# ------------------------------------------------------------

notificationManager.send(
    force_daily=FORCE_DAILY_UPDATE
)
