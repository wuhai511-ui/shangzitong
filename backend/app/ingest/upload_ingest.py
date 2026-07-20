"""Upload ingest — smart column detection and file parsing."""
import csv
import io
import re
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ParseResult:
    """Result of parsing an uploaded file."""
    headers: list[str]
    rows: list[dict]
    mappings: dict
    total_rows: int
    errors: list[str] = field(default_factory=list)


class UploadIngest:
    """Parse uploaded CSV/Excel files with intelligent column recognition."""

    DATE_KEYWORDS = ['日期', 'date', '时间', 'time', '交易日', 'settle']
    AMOUNT_KEYWORDS = ['金额', 'amount', 'money', '交易金额', 'sum']

    def _auto_detect_columns(self, df: pd.DataFrame) -> dict:
        """Detect date and amount columns by keyword matching.

        Returns:
            dict with 'date_column' and 'amount_column' keys (None if not detected).
        """
        date_col = None
        amount_col = None
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if date_col is None:
                for kw in self.DATE_KEYWORDS:
                    if kw.lower() in col_lower:
                        date_col = col
                        break
            if amount_col is None:
                for kw in self.AMOUNT_KEYWORDS:
                    if kw.lower() in col_lower:
                        amount_col = col
                        break
        return {'date_column': date_col, 'amount_column': amount_col}

    def _guess_date_format(self, sample: str) -> str:
        """Guess date format string from a sample value.

        Supported formats:
            yyyy-MM-dd, yyyy/MM/dd, yyyy.MM.dd, yyyyMMdd, MM-dd-yyyy
        """
        s = str(sample).strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
            return "%Y-%m-%d"
        if re.match(r'^\d{4}/\d{2}/\d{2}$', s):
            return "%Y/%m/%d"
        if re.match(r'^\d{4}\.\d{2}\.\d{2}$', s):
            return "%Y.%m.%d"
        if re.match(r'^\d{8}$', s):
            return "%Y%m%d"
        if re.match(r'^\d{2}-\d{2}-\d{4}$', s):
            return "%m-%d-%Y"
        return "%Y-%m-%d"

    def _clean_amount(self, val: str) -> float:
        """Clean amount string: remove commas, currency symbols, whitespace."""
        s = str(val).strip()
        for ch in [',', '¥', '￥', '$', '€', ' ']:
            s = s.replace(ch, '')
        return float(s)

    def parse_upload(self, file_content, filename, template=None, encoding='utf-8-sig') -> ParseResult:
        """Parse an uploaded file (CSV or Excel) and return ParseResult.

        Args:
            file_content: Raw bytes of the uploaded file.
            filename: Original filename (used to detect type).
            template: Optional template name for column mapping hint.
            encoding: Text encoding for CSV files (default utf-8-sig).

        Returns:
            ParseResult with detected headers, rows, mappings, and errors.
        """
        errors: list[str] = []
        try:
            if filename.lower().endswith('.csv'):
                text = file_content.decode(encoding)
                reader = csv.DictReader(io.StringIO(text))
                headers = reader.fieldnames or []
                rows = list(reader)
            else:
                df_excel = pd.read_excel(io.BytesIO(file_content), dtype=str)
                headers = list(df_excel.columns)
                rows = df_excel.to_dict('records')
        except Exception as e:
            return ParseResult(
                headers=[], rows=[], mappings={}, total_rows=0,
                errors=[str(e)],
            )

        df = pd.DataFrame(rows, columns=list(headers))
        mappings = self._auto_detect_columns(df)
        return ParseResult(
            headers=headers,
            rows=rows,
            mappings=mappings,
            total_rows=len(rows),
            errors=errors,
        )
