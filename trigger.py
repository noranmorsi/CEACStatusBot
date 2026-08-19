import json
import os
import subprocess
import zipfile

from dotenv import load_dotenv

from CEACStatusBot import (
    EmailNotificationHandle,
    NotificationManager,
    TelegramNotificationHandle,
)


# ------------------------------------------------------------
# Load .env if present, otherwise use GitHub/system environment
# ------------------------------------------------------------

if os.path.exists(".env"):
    load_dotenv(dotenv_path=".env")
else:
    print(".env not found, using system environment only")


# ------------------------------------------------------------
# Download the most recent status artifact
# ------------------------------------------------------------

def download_artifact():
    try:
        repository = os.environ["GITHUB_REPOSITORY"]

        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repository}/actions/artifacts",
                "--paginate",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        artifacts_data = json.loads(result.stdout)

        status_artifacts = [
            artifact
            for artifact in artifacts_data.get("artifacts", [])
            if artifact.get("name") == "status-artifact"
            and not artifact.get("expired", False)
        ]

        if not status_artifacts:
            print("No previous status artifact found.")

            with open("status_record.json", "w") as file:
                json.dump({"statuses": []}, file)

            return

        # Use the most recently created status artifact.
        status_artifacts.sort(
            key=lambda artifact: artifact.get("created_at", ""),
            reverse=True,
        )

        latest_artifact = status_artifacts[0]
        artifact_id = latest_artifact["id"]

        print(
            f"Downloading previous status artifact "
            f"{artifact_id} created at "
            f"{latest_artifact.get('created_at')}"
        )

        # Download the artifact ZIP.
        subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repository}/actions/artifacts/"
                f"{artifact_id}/zip",
                "--output",
                "status_artifact.zip",
            ],
            check=True,
        )

        # Extract status_record.json.
        with zipfile.ZipFile(
            "status_artifact.zip",
            "r",
        ) as archive:
            archive.extractall(".")

        if os.path.exists("status_record.json"):
            print(
                "Previous status_record.json "
                "downloaded successfully."
            )
        else:
            print(
                "Artifact downloaded, but "
                "status_record.json was not found."
            )

            with open("status_record.json", "w") as file:
                json.dump({"statuses": []}, file)

    except Exception as e:
        print(f"Error downloading artifact: {e}")

        # Start fresh if the previous artifact cannot be retrieved.
        with open("status_record.json", "w") as file:
            json.dump({"statuses": []}, file)


# ------------------------------------------------------------
# GitHub token
# ------------------------------------------------------------

GH_TOKEN = os.getenv("GH_TOKEN")

if not GH_TOKEN:
    print("GH_TOKEN not found")


# ------------------------------------------------------------
# Get previous status record
# ------------------------------------------------------------

if not os.path.exists("status_record.json"):
    download_artifact()


# ------------------------------------------------------------
# Required CEAC environment variables
# ------------------------------------------------------------

try:
    LOCATION = os.environ["LOCATION"]
    NUMBER = os.environ["NUMBER"]
    PASSPORT_NUMBER = os.environ["PASSPORT_NUMBER"]
    SURNAME = os.environ["SURNAME"]

    notificationManager = NotificationManager(
        LOCATION,
        NUMBER,
        PASSPORT_NUMBER,
        SURNAME,
    )

except KeyError as e:
    raise RuntimeError(
        f"Missing required env var: {e}"
    ) from e


# ------------------------------------------------------------
# Optional: Email notifications
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
        "Email notification config "
        "missing or incomplete"
    )


# ------------------------------------------------------------
# Optional: Telegram notifications
# ------------------------------------------------------------

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

if BOT_TOKEN and CHAT_ID:
    tgNotif = TelegramNotificationHandle(
        BOT_TOKEN,
        CHAT_ID,
    )

    notificationManager.addHandle(tgNotif)
else:
    print(
        "Telegram bot notification config "
        "missing or incomplete"
    )


# ------------------------------------------------------------
# Daily update mode
#
# The daily GitHub Actions workflow should set:
#
# FORCE_DAILY_UPDATE: "true"
#
# The normal hourly workflow does not set this variable.
# ------------------------------------------------------------

FORCE_DAILY_UPDATE = (
    os.getenv(
        "FORCE_DAILY_UPDATE",
        "",
    ).lower()
    == "true"
)


# ------------------------------------------------------------
# Run CEAC check and send notifications
# ------------------------------------------------------------

notificationManager.send(
    force_daily=FORCE_DAILY_UPDATE
)
