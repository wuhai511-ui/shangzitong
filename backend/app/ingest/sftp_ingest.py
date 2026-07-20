"""SFTP poller — download settlement files and ingest via UploadIngest."""
import fnmatch
import io
from datetime import datetime
from typing import Optional

import paramiko

from .upload_ingest import UploadIngest


class SftpPoller:
    """Poll an SFTP server, download new settlement files, parse and deduplicate."""

    def __init__(self, host: str, port: int, username: str, password: Optional[str],
                 remote_path: str, file_pattern: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.remote_path = remote_path.rstrip("/") or "/"
        self.file_pattern = file_pattern or "*.csv"
        self._transport: Optional[paramiko.Transport] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def connect(self) -> None:
        self._transport = paramiko.Transport((self.host, self.port))
        self._transport.connect(username=self.username, password=self.password)
        self._sftp = paramiko.SFTPClient.from_transport(self._transport)

    def disconnect(self) -> None:
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._transport:
            self._transport.close()
            self._transport = None

    def _is_connected(self) -> bool:
        return self._sftp is not None and self._transport is not None

    def _match_pattern(self, filename: str) -> bool:
        return fnmatch.fnmatch(filename.lower(), self.file_pattern.lower())

    def _detect_encoding(self, file_bytes: bytes, filename: str) -> str:
        if filename.lower().endswith('.csv'):
            for enc in ('utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1'):
                try:
                    file_bytes.decode(enc)
                    return enc
                except (UnicodeDecodeError, LookupError):
                    continue
        return 'utf-8-sig'

    def test_connection(self) -> tuple[bool, str, list[str]]:
        try:
            self.connect()
            if not self._sftp:
                return False, "SFTP client not initialized", []
            files = self._sftp.listdir(self.remote_path)
            matched = [f for f in files if self._match_pattern(f) and not self._is_dir(f)]
            return True, "connected", matched
        except Exception as e:
            return False, str(e), []
        finally:
            self.disconnect()

    def _is_dir(self, filename: str) -> bool:
        try:
            path = f"{self.remote_path}/{filename}"
            return self._sftp is not None and self._sftp.stat(path).st_mode & 0o40000 != 0
        except (IOError, OSError):
            return False

    def poll(self, source_id: int, user_id: int, db_session,
             ingest: Optional[UploadIngest] = None) -> dict:
        """Download and ingest new files from the SFTP server.

        Returns:
            dict with files_processed, settlements_imported, errors.
        """
        if ingest is None:
            ingest = UploadIngest()

        errors: list[str] = []
        files_processed = 0
        settlements_imported = 0

        try:
            self.connect()
            if not self._sftp:
                return {"files_processed": 0, "settlements_imported": 0,
                        "errors": ["failed to connect"]}

            all_files = self._sftp.listdir(self.remote_path)
            candidate_files = [f for f in all_files
                               if self._match_pattern(f) and not self._is_dir(f)]

            for filename in sorted(candidate_files):
                try:
                    imported = self._process_file(
                        filename, source_id, user_id, db_session, ingest)
                    if imported >= 0:
                        files_processed += 1
                        settlements_imported += imported
                except Exception as e:
                    errors.append(f"{filename}: {e}")

        except Exception as e:
            errors.append(str(e))
        finally:
            self.disconnect()

        return {
            "files_processed": files_processed,
            "settlements_imported": settlements_imported,
            "errors": errors,
        }

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

    def _process_file(self, filename: str, source_id: int, user_id: int,
                      db_session, ingest: UploadIngest) -> int:
        from models.datasource import Settlement
        from decimal import Decimal

        remote_path = f"{self.remote_path}/{filename}"
        file_obj = io.BytesIO()
        self._sftp.getfo(remote_path, file_obj)  # type: ignore[union-attr]
        file_bytes = file_obj.getvalue()

        existing = db_session.query(Settlement).filter(
            Settlement.source_id == source_id,
            Settlement.user_id == user_id,
            Settlement.batch_hash == filename,
        ).first()
        if existing:
            return 0

        encoding = self._detect_encoding(file_bytes, filename)
        result = ingest.parse_upload(file_bytes, filename, encoding=encoding)

        if result.errors:
            return -1

        imported = 0
        date_col = result.mappings.get("date_column")
        amount_col = result.mappings.get("amount_column")
        if not date_col or not amount_col:
            return 0

        for row in result.rows:
            try:
                parsed_date = self._parse_date(str(row.get(date_col, "")))
                if parsed_date is None:
                    continue
                settle_date = parsed_date.date()
                amount = Decimal(str(row.get(amount_col, 0))
                                 .replace(",", "").replace("¥", ""))
            except (ValueError, KeyError):
                continue

            dup = db_session.query(Settlement).filter(
                Settlement.source_id == source_id,
                Settlement.settle_date == settle_date,
                Settlement.amount == amount,
                Settlement.user_id == user_id,
            ).first()
            if dup:
                continue

            s = Settlement(
                source_id=source_id,
                user_id=user_id,
                settle_date=settle_date,
                amount=amount,
                batch_hash=filename,
            )
            db_session.add(s)
            imported += 1

        return imported
