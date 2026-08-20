import datetime
import json
import os

import pytz

from CEACStatusBot.captcha import CaptchaHandle, OnnxCaptchaHandle
from CEACStatusBot.request import query_status


class NotificationManager:
    def __init__(
        self,
        location: str,
        number: str,
        passport_number: str,
        surname: str,
        captchaHandle: CaptchaHandle = OnnxCaptchaHandle("captcha.onnx"),
    ) -> None:

        self.__location = location
        self.__number = number
        self.__passport_number = passport_number
        self.__surname = surname

        self.__captchaHandle = captchaHandle

        self.__status_file = "status_record.json"

    def send(
        self,
        force_daily: bool = False,
    ) -> None:

        # Query CEAC
        res = query_status(
            self.__location,
            self.__number,
            self.__passport_number,
            self.__surname,
            self.__captchaHandle,
        )

        if not res["success"]:
            raise RuntimeError(
                "Query status failed."
            )

        current_status = res["status"]
        current_last_updated = res["case_last_updated"]

        print(
            f"Current status: {current_status} "
            f"- Last updated: {current_last_updated}"
        )

        # Load previous status
        statuses = self.__load_statuses()

        previous_status = None
        previous_last_updated = None

        if statuses:
            previous_status = statuses[-1].get("status")
            previous_last_updated = statuses[-1].get("last_updated")

        # Determine whether CEAC changed
        status_changed = (
            previous_status != current_status
            or previous_last_updated != current_last_updated
        )

        print(f"Previous status: {previous_status}")
        print(f"Previous last updated: {previous_last_updated}")
        print(f"Status changed: {status_changed}")
        print(f"Force daily update: {force_daily}")

        # Save current status if it changed
        if status_changed:
            self.__save_current_status(
                current_status,
                current_last_updated,
            )

        # No notifications are sent.
        if status_changed:
            print("CEAC status changed. Status record updated.")
        else:
            print("Status unchanged. No notification sent.")

    def __load_statuses(self) -> list:

        if not os.path.exists(self.__status_file):
            return []

        try:
            with open(self.__status_file, "r") as file:
                data = json.load(file)

            return data.get("statuses", [])

        except (json.JSONDecodeError, OSError):

            print(
                "Could not read status_record.json. "
                "Starting with empty status history."
            )

            return []

    def __save_current_status(
        self,
        status: str,
        last_updated: str,
    ) -> None:

        statuses = self.__load_statuses()

        cairo = pytz.timezone("Africa/Cairo")
        now = datetime.datetime.now(cairo)

        statuses.append(
            {
                "status": status,
                "last_updated": last_updated,
                "date": now.isoformat(),
            }
        )

        # Keep only the most recent 100 records.
        statuses = statuses[-100:]

        with open(self.__status_file, "w") as file:
            json.dump(
                {
                    "statuses": statuses
                },
                file,
                indent=2,
            )

        print("Updated status_record.json")
