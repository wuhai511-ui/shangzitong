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

    def parse_upload(
        self,
        file_content,
        filename,
        template=None,
        encoding='utf-8-sig',
        max_rows=None,
        max_columns=None,
        max_cells=None,
    ) -> ParseResult:
        """Parse an uploaded file (CSV or Excel) and return ParseResult.

        Args:
            file_content: Raw bytes of the uploaded file.
            filename: Original filename (used to detect type).
            template: Optional template name for column mapping hint.
            encoding: Text encoding for CSV files (default utf-8-sig).
            max_rows: Optional maximum data rows; one extra row detects overflow.
            max_columns: Optional maximum number of columns.
            max_cells: Optional maximum rows-by-columns cell budget.

        Returns:
            ParseResult with detected headers, rows, mappings, and errors.
        """
        def limit_error(message):
            return ParseResult(
                headers=[], rows=[], mappings={}, total_rows=0, errors=[message]
            )

        errors: list[str] = []
        try:
            if filename.lower().endswith('.csv'):
                text_stream = io.TextIOWrapper(
                    io.BytesIO(file_content), encoding=encoding, newline=""
                )
                reader = csv.DictReader(text_stream)
                headers = reader.fieldnames or []
                column_count = len(headers)
                if max_columns is not None and column_count > max_columns:
                    return limit_error("Upload exceeds column limit")

                rows = []
                cell_count = 0
                for row_number, row in enumerate(reader, start=1):
                    if max_rows is not None and row_number > max_rows:
                        return limit_error("Upload exceeds row limit")
                    cell_count += column_count
                    if max_cells is not None and cell_count > max_cells:
                        return limit_error("Upload exceeds cell limit")
                    rows.append(row)
            else:
                read_options = {"dtype": str}
                if max_rows is not None:
                    read_options["nrows"] = max_rows + 1
                df_excel = pd.read_excel(io.BytesIO(file_content), **read_options)
                headers = list(df_excel.columns)
                column_count = len(headers)
                row_count = len(df_excel.index)
                if max_columns is not None and column_count > max_columns:
                    return limit_error("Upload exceeds column limit")
                if max_rows is not None and row_count > max_rows:
                    return limit_error("Upload exceeds row limit")
                if max_cells is not None and row_count * column_count > max_cells:
                    return limit_error("Upload exceeds cell limit")
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
