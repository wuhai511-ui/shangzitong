"""Email poller — scan inbox for settlement emails, download attachments and ingest."""
import email
import email.utils
import hashlib
import imaplib
import io
from datetime import datetime
from typing import Optional

from .upload_ingest import UploadIngest


class EmailPoller:
    """Poll an IMAP inbox, download settlement CSV/Excel attachments, parse and deduplicate."""

    def __init__(self, imap_host: str, imap_port: int, username: str,
                 password: str, use_ssl: bool = True):
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self._conn: Optional[imaplib.IMAP4] = None

    def connect(self) -> None:
        if self.use_ssl:
            self._conn = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        else:
            self._conn = imaplib.IMAP4(self.imap_host, self.imap_port)
        self._conn.login(self.username, self.password)

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def _is_connected(self) -> bool:
        return self._conn is not None

    def test_connection(self) -> tuple[bool, str, int]:
        try:
            self.connect()
            if not self._conn:
                return False, "IMAP client not initialized", 0
            status, data = self._conn.select("INBOX")
            if status != "OK":
                return False, "failed to select INBOX", 0
            count = int(data[0]) if data and data[0] else 0
            return True, "connected", count
        except Exception as e:
            return False, str(e), 0
        finally:
            self.disconnect()

    @staticmethod
    def _decode_header(value: str) -> str:
        decoded_parts = email.header.decode_header(value)
        result_parts: list[str] = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result_parts.append(part.decode(charset or "utf-8", errors="replace"))
                except (LookupError, UnicodeDecodeError):
                    result_parts.append(part.decode("utf-8", errors="replace"))
            else:
                result_parts.append(str(part))
        return "".join(result_parts)

    @staticmethod
    def _make_batch_hash(subject: str, date_str: str) -> str:
        raw = f"{subject.strip()}|{date_str.strip()}"
        return hashlib.md5(raw.encode("utf-8", errors="replace")).hexdigest()[:24]

    def _attachment_matches(self, filename: str) -> bool:
        lower = filename.lower()
        return lower.endswith(".csv") or lower.endswith(".xlsx") or lower.endswith(".xls")

    def poll(self, source_id: int, user_id: int, db_session,
             ingest: Optional[UploadIngest] = None) -> dict:
        """Scan inbox for settlement emails, download and ingest attachments.

        Returns:
            dict with emails_processed, settlements_imported, errors.
        """
        if ingest is None:
            ingest = UploadIngest()

        errors: list[str] = []
        emails_processed = 0
        settlements_imported = 0

        try:
            self.connect()
            if not self._conn:
                return {"emails_processed": 0, "settlements_imported": 0,
                        "errors": ["failed to connect"]}

            status, _ = self._conn.select("INBOX")
            if status != "OK":
                return {"emails_processed": 0, "settlements_imported": 0,
                        "errors": ["failed to select INBOX"]}

            status, msg_ids = self._conn.search(None, "ALL")
            if status != "OK" or not msg_ids or not msg_ids[0]:
                return {"emails_processed": 0, "settlements_imported": 0,
                        "errors": []}

            from models.datasource import Settlement

            for num in sorted(msg_ids[0].split(), reverse=True):
                try:
                    status, data = self._conn.fetch(num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE MESSAGE-ID)])")
                    if status != "OK" or not data or not data[0]:
                        continue

                    header_bytes = None
                    for item in data:
                        if isinstance(item, tuple):
                            header_bytes = item[1]
                            break
                    if header_bytes is None:
                        continue

                    parser = email.parser.BytesHeaderParser()
                    msg_header = parser.parsebytes(header_bytes)

                    subject = self._decode_header(msg_header.get("Subject", ""))
                    date_str = msg_header.get("Date", "")
                    message_id = msg_header.get("Message-ID", "")

                    if not subject and not message_id:
                        continue

                    batch_hash = self._make_batch_hash(subject, date_str)

                    existing = db_session.query(Settlement).filter(
                        Settlement.source_id == source_id,
                        Settlement.user_id == user_id,
                        Settlement.batch_hash == batch_hash,
                    ).first()
                    if existing:
                        continue

                    file_bytes_list = self._fetch_attachments(num, errors)
                    if not file_bytes_list:
                        db_session.add(Settlement(
                            source_id=source_id,
                            user_id=user_id,
                            settle_date=datetime.utcnow().date(),
                            amount=0,
                            batch_hash=batch_hash,
                        ))
                        db_session.flush()
                        emails_processed += 1
                        continue

                    email_imported = 0
                    for filename, file_bytes in file_bytes_list:
                        try:
                            encoding = self._detect_encoding(file_bytes, filename)
                            result = ingest.parse_upload(file_bytes, filename, encoding=encoding)
                            if result.errors:
                                errors.append(f"{filename}: {'; '.join(result.errors)}")
                                continue

                            date_col = result.mappings.get("date_column")
                            amount_col = result.mappings.get("amount_column")
                            if not date_col or not amount_col:
                                continue

                            imported = self._insert_settlements(
                                result, date_col, amount_col,
                                source_id, user_id, batch_hash, db_session)
                            email_imported += imported
                        except Exception as e:
                            errors.append(f"{filename}: {e}")

                    if email_imported == 0 and email_imported == 0:
                        pass

                    settlements_imported += email_imported
                    emails_processed += 1

                except Exception as e:
                    errors.append(f"email #{num.decode() if isinstance(num, bytes) else num}: {e}")

        except Exception as e:
            errors.append(str(e))
        finally:
            self.disconnect()

        return {
            "emails_processed": emails_processed,
            "settlements_imported": settlements_imported,
            "errors": errors,
        }

    def _fetch_attachments(self, msg_num, errors: list[str]) -> list[tuple[str, bytes]]:
        status, data = self._conn.fetch(msg_num, "(BODY.PEEK[])")
        if status != "OK" or not data or not data[0]:
            return []

        raw_bytes = None
        for item in data:
            if isinstance(item, tuple):
                raw_bytes = item[1]
                break
        if raw_bytes is None:
            return []

        msg = email.message_from_bytes(raw_bytes)
        attachments: list[tuple[str, bytes]] = []

        for part in msg.walk():
            content_disposition = part.get_content_disposition()
            if content_disposition != "attachment":
                continue

            filename = part.get_filename()
            if filename is None:
                continue

            filename_decoded = self._decode_header(filename)
            if not self._attachment_matches(filename_decoded):
                continue

            payload = part.get_payload(decode=True)
            if payload:
                attachments.append((filename_decoded, payload))

        return attachments

    def _detect_encoding(self, file_bytes: bytes, filename: str) -> str:
        if filename.lower().endswith(".csv"):
            for enc in ("utf-8-sig", "utf-8", "gbk", "gb2312", "latin-1"):
                try:
                    file_bytes.decode(enc)
                    return enc
                except (UnicodeDecodeError, LookupError):
                    continue
        return "utf-8-sig"

    def _insert_settlements(self, result, date_col: str, amount_col: str,
                            source_id: int, user_id: int, batch_hash: str,
                            db_session) -> int:
        from models.datasource import Settlement
        from decimal import Decimal

        imported = 0
        for row in result.rows:
            try:
                date_str = str(row.get(date_col, "")).strip()
                settle_date = self._parse_date(date_str)
                if settle_date is None:
                    continue
                amount = Decimal(str(row.get(amount_col, 0))
                                 .replace(",", "").replace("¥", ""))
            except (ValueError, KeyError):
                continue

            dup = db_session.query(Settlement).filter(
                Settlement.source_id == source_id,
                Settlement.settle_date == settle_date.date(),
                Settlement.amount == amount,
                Settlement.user_id == user_id,
            ).first()
            if dup:
                continue

            s = Settlement(
                source_id=source_id,
                user_id=user_id,
                settle_date=settle_date.date(),
                amount=amount,
                batch_hash=batch_hash,
            )
            db_session.add(s)
            imported += 1

        return imported

    DATE_FORMATS = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d",
        "%m-%d-%Y", "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%Y",
    ]

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        s = date_str.strip()
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None
