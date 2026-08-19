from smtplib import SMTP_SSL
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

from .handle import NotificationHandle


class EmailNotificationHandle(NotificationHandle):
    def __init__(
        self,
        fromEmail: str,
        toEmail: str,
        emailPassword: str,
        hostAddress: str = "",
    ) -> None:
        super().__init__()

        self.__fromEmail = fromEmail
        self.__toEmail = toEmail.split("|")
        self.__emailPassword = emailPassword

        self.__hostAddress = (
            hostAddress
            or "smtp." + fromEmail.split("@")[1]
        )

        if ":" in self.__hostAddress:
            addr, port = self.__hostAddress.split(":")
            self.__hostAddress = addr
            self.__hostPort = int(port)
        else:
            self.__hostPort = 0

    def send(self, result):
        # ------------------------------------------------------------
        # Email subject
        # ------------------------------------------------------------

        mail_title = "{} : {}".format(
            result["application_num_origin"],
            result["status"],
        )

        # ------------------------------------------------------------
        # Email content
        # ------------------------------------------------------------

        status = result.get("status", "Unknown")
        case_last_updated = result.get(
            "case_last_updated",
            "Unknown",
        )
        description = result.get(
            "description",
            "",
        )

        # Convert the CEAC Markdown-style link into a normal URL.
        description = description.replace(
            "[TRAVEL.STATE.GOV](https://TRAVEL.STATE.GOV)",
            "TRAVEL.STATE.GOV (https://TRAVEL.STATE.GOV)",
        )

        mail_content = (
            f"Status: {status}\n"
            f"Case Last Updated: {case_last_updated}\n\n"
            f"Description:\n"
            f"{description}"
        )

        # ------------------------------------------------------------
        # Build email
        # ------------------------------------------------------------

        msg = MIMEMultipart()

        msg["Subject"] = Header(
            mail_title,
            "utf-8",
        )

        msg["From"] = self.__fromEmail
        msg["To"] = ";".join(self.__toEmail)

        msg.attach(
            MIMEText(
                mail_content,
                "plain",
                "utf-8",
            )
        )

        # ------------------------------------------------------------
        # Send email
        # ------------------------------------------------------------

        smtp = SMTP_SSL(
            self.__hostAddress,
            self.__hostPort,
        )

        print(
            smtp.login(
                self.__fromEmail,
                self.__emailPassword,
            )
        )

        print(
            smtp.sendmail(
                self.__fromEmail,
                self.__toEmail,
                msg.as_string(),
            )
        )

        smtp.quit()
