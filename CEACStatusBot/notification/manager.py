import json
import os
import datetime

import pytz

from CEACStatusBot.captcha import CaptchaHandle, OnnxCaptchaHandle
from CEACStatusBot.request import query_status

from .handle import NotificationHandle


DEFAULT_ACTIVE_HOURS = "00:00-23:59"
CAIRO_TIMEZONE = "Africa/Cairo"


class NotificationManager:
    def __init__(
        self,
        location: str,
        number: str,
        passport_number: str,
        surname: str,
        captchaHandle: CaptchaHandle = OnnxCaptchaHandle("captcha.onnx"),
    ) -> None:
        self.__handleList = []
        self.__location = location
        self.__number = number
        self.__captchaHandle = captchaHandle
        self.__passport_number = passport_number
        self.__surname = surname
        self.__status_file = "status_record.json"

    def _get_hour_range(self) -> list:
        active_hours = os.getenv("ACTIVE_HOURS")

        if active_hours is None:
            active_hours = DEFAULT_ACTIVE_HOURS

        start_str, end_str = active_hours.split("-")

        start = datetime.datetime.strptime(
            start_str,
            "%H:%M",
        ).time()

        end = datetime.datetime.strptime(
            end_str,
            "%H:%M",
        ).time()

        if start > end:
            raise ValueError(
                f"Start time must be before end time, "
                f"got start: {start}, end: {end}"
            )

        return start, end

    def addHandle(
        self,
        notificationHandle: NotificationHandle,
    ) -> None:
        self.__handleList.append(notificationHandle)

    def send(
        self,
        force_daily: bool = False,
    ) -> None:
        # --- Query CEAC ---
        res = query_status(
            self.__location,
            self.__number,
            self.__passport_number,
            self.__surname,
            self.__captchaHandle,
        )

        if not res["success"]:
            raise RuntimeError(
                "Query status failed, no notification sent."
            )

        current_status = res["status"]
        current_last_updated = res["case_last_updated"]

        print(
            f"Current status: {current_status} - "
            f"Last updated: {current_last_updated}"
        )

        # --- Load previous statuses ---
        statuses = self.__load_statuses()

        # --- Determine whether CEAC information changed ---
        status_changed = (
            not statuses
            or current_status
            != statuses[-1].get("status", None)
            or current_last_updated
            != statuses[-1].get("last_updated", None)
        )

        # ============================================================
        # DAILY UPDATE MODE
        # ============================================================
        #
        # The daily workflow sets:
        #
        # FORCE_DAILY_UPDATE=true
        #
        # We only send the daily notification when the current Cairo
        # time is between 17:00 and 17:59.
        #
        # This protects against the workflow being triggered twice
        # because of daylight-saving/cron handling.
        # ============================================================

        daily_update = False

        if force_daily:
            try:
                local_timezone = pytz.timezone(
                    CAIRO_TIMEZONE
                )

                local_time = datetime.datetime.now(
                    local_timezone
                )

                print(
                    f"Current Cairo time: "
                    f"{local_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                if local_time.hour == 17:
                    daily_update = True
                    print(
                        "5 PM Cairo daily update: "
                        "notification will be sent."
                    )
                else:
                    print(
                        "Daily workflow ran outside the 5 PM Cairo "
                        "window. No daily notification sent."
                    )

            except Exception as e:
                print(
                    f"Unable to determine Cairo time: {e}"
                )

        # ============================================================
        # NOTIFICATION LOGIC
        # ============================================================

        if status_changed:
            # Save the new status whenever CEAC changes.
            self.__save_current_status(
                current_status,
                current_last_updated,
            )

            print(
                "Status changed. Sending notification."
            )

            self.__send_notifications(res)

        elif daily_update:
            # Status has NOT changed, but this is the daily 5 PM check.
            print(
                "Status unchanged, but sending daily 5 PM update."
            )

            self.__send_notifications(res)

        else:
            print(
                "Status unchanged. No notification sent."
            )

    def __load_statuses(self) -> list:
        if os.path.exists(self.__status_file):
            with open(
                self.__status_file,
                "r",
            ) as file:
                return json.load(file).get(
                    "statuses",
                    [],
                )

        return []

    def __save_current_status(
        self,
        status: str,
        last_updated: str,
    ) -> None:
        statuses = self.__load_statuses()

        statuses.append(
            {
                "status": status,
                "last_updated": last_updated,
                "date": datetime.datetime.now().isoformat(),
            }
        )

        with open(
            self.__status_file,
            "w",
        ) as file:
            json.dump(
                {"statuses": statuses},
                file,
            )

    def __send_notifications(
        self,
        res: dict,
    ) -> None:

        # ------------------------------------------------------------
        # Refused status active-hours protection
        # ------------------------------------------------------------

        if res["status"] == "Refused":

            try:
                timezone_name = os.environ.get(
                    "TIMEZONE",
                    CAIRO_TIMEZONE,
                )

                localTimeZone = pytz.timezone(
                    timezone_name
                )

                localTime = datetime.datetime.now(
                    localTimeZone
                )

            except pytz.exceptions.UnknownTimeZoneError:

                print(
                    f"UNKNOWN TIMEZONE '{timezone_name}'. "
                    f"Using {CAIRO_TIMEZONE}."
                )

                localTimeZone = pytz.timezone(
                    CAIRO_TIMEZONE
                )

                localTime = datetime.datetime.now(
                    localTimeZone
                )

            except KeyError:

                print(
                    f"TIMEZONE not set. "
                    f"Using {CAIRO_TIMEZONE}."
                )

                localTimeZone = pytz.timezone(
                    CAIRO_TIMEZONE
                )

                localTime = datetime.datetime.now(
                    localTimeZone
                )

            active_hour_start, active_hour_end = (
                self._get_hour_range()
            )

            start_dt = datetime.datetime.combine(
                localTime.date(),
                active_hour_start,
            ).replace(
                tzinfo=localTimeZone
            )

            end_dt = datetime.datetime.combine(
                localTime.date(),
                active_hour_end,
            ).replace(
                tzinfo=localTimeZone
            )

            if not (
                start_dt
                <= localTime
                <= end_dt
            ):
                print(
                    f"Outside active hours "
                    f"{os.getenv('ACTIVE_HOURS', DEFAULT_ACTIVE_HOURS)}. "
                    "No notification sent for Refused status."
                )

                return

        # ------------------------------------------------------------
        # Send through every configured notification method
        # ------------------------------------------------------------

        if not self.__handleList:
            print(
                "No notification handles configured."
            )

            return

        for notificationHandle in self.__handleList:
            notificationHandle.send(res)
