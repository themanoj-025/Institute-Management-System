"""Tests for the unified ExportService (services/export_service.py)."""

import os
import tempfile

import pytest

from services.export_service import ExportError, ExportService

# Fixtures


@pytest.fixture
def export_service():
    """Create an ExportService with a temporary export directory."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield ExportService(export_dir=tmpdir, auto_create=True)


SAMPLE_HEADERS = ["Name", "Grade", "Subject"]
SAMPLE_ROWS = [
    ["Alice", "A", "Mathematics"],
    ["Bob", "B+", "Physics"],
    ["Charlie", "A-", "Chemistry"],
    ["Diana", "B", "Biology"],
]


# CSV Tests


class TestCsvExport:
    def test_to_csv_creates_file(self, export_service):
        result = export_service.to_csv("test.csv", SAMPLE_HEADERS, SAMPLE_ROWS)
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.mime_type == ExportService.MIME_CSV
        assert result.filename == "test.csv"

    def test_to_csv_content(self, export_service):
        result = export_service.to_csv("content.csv", SAMPLE_HEADERS, SAMPLE_ROWS)
        with open(result.path, encoding="utf-8") as f:
            content = f.read()
        assert "Name,Grade,Subject" in content
        assert "Alice,A,Mathematics" in content

    def test_to_csv_bytes(self, export_service):
        result = export_service.to_csv_bytes(SAMPLE_HEADERS, SAMPLE_ROWS)
        assert result.path is None
        assert result.bytes_ is not None
        text = result.bytes_.decode("utf-8")
        assert "Name,Grade,Subject" in text
        assert "Charlie,A-,Chemistry" in text

    def test_to_csv_empty_rows(self, export_service):
        result = export_service.to_csv("empty.csv", SAMPLE_HEADERS, [])
        with open(result.path, encoding="utf-8") as f:
            content = f.read()
        # Accept both Windows (CRLF) and Unix (LF) line endings
        assert content in ("Name,Grade,Subject\r\n", "Name,Grade,Subject\n")

    def test_to_csv_bytes_empty(self, export_service):
        result = export_service.to_csv_bytes(SAMPLE_HEADERS, [])
        text = result.bytes_.decode("utf-8")
        assert "Name,Grade,Subject" in text


# Excel Tests


class TestExcelExport:
    def test_to_excel_creates_file(self, export_service):
        result = export_service.to_excel("test.xlsx", SAMPLE_HEADERS, SAMPLE_ROWS)
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.mime_type == ExportService.MIME_XLSX

    def test_to_excel_bytes(self, export_service):
        result = export_service.to_excel_bytes(SAMPLE_HEADERS, SAMPLE_ROWS)
        assert result.path is None
        assert result.bytes_ is not None
        # Should be a valid .xlsx (starts with PK zip signature)
        assert result.bytes_[:2] == b"PK"

    def test_to_excel_empty_rows(self, export_service):
        result = export_service.to_excel("empty.xlsx", SAMPLE_HEADERS, [])
        assert os.path.exists(result.path)

    def test_to_excel_custom_sheet_name(self, export_service):
        result = export_service.to_excel(
            "custom_sheet.xlsx", SAMPLE_HEADERS, SAMPLE_ROWS, sheet_name="Students"
        )
        assert os.path.exists(result.path)

        import openpyxl

        wb = openpyxl.load_workbook(result.path)
        try:
            assert "Students" in wb.sheetnames
        finally:
            wb.close()


# PDF Tests


class TestPdfExport:
    def test_to_pdf_creates_file(self, export_service):
        result = export_service.to_pdf("test.pdf", "Report", SAMPLE_HEADERS, SAMPLE_ROWS)
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.mime_type == ExportService.MIME_PDF

    def test_to_pdf_bytes(self, export_service):
        result = export_service.to_pdf_bytes("Report", SAMPLE_HEADERS, SAMPLE_ROWS)
        assert result.path is None
        assert result.bytes_ is not None
        # PDFs start with %PDF
        assert result.bytes_[:4] == b"%PDF"

    def test_to_pdf_empty_rows(self, export_service):
        result = export_service.to_pdf("empty.pdf", "Empty", SAMPLE_HEADERS, [])
        assert os.path.exists(result.path)

    def test_to_pdf_landscape(self, export_service):
        result = export_service.to_pdf(
            "landscape.pdf",
            "Landscape Report",
            SAMPLE_HEADERS,
            SAMPLE_ROWS,
            landscape=True,
        )
        assert os.path.exists(result.path)

    def test_to_pdf_bytes_landscape(self, export_service):
        result = export_service.to_pdf_bytes(
            "Landscape", SAMPLE_HEADERS, SAMPLE_ROWS, landscape=True
        )
        assert result.bytes_ is not None
        assert result.bytes_[:4] == b"%PDF"


# Auto-detect export


class TestAutoExport:
    def test_export_csv_by_extension(self, export_service):
        result = export_service.export("data.csv", SAMPLE_HEADERS, SAMPLE_ROWS)
        assert result.mime_type == ExportService.MIME_CSV
        assert result.path is not None
        assert result.path.endswith(".csv")

    def test_export_excel_by_extension(self, export_service):
        result = export_service.export("data.xlsx", SAMPLE_HEADERS, SAMPLE_ROWS)
        assert result.mime_type == ExportService.MIME_XLSX
        assert result.path is not None
        assert result.path.endswith(".xlsx")

    def test_export_pdf_by_extension(self, export_service):
        result = export_service.export("data.pdf", SAMPLE_HEADERS, SAMPLE_ROWS)
        assert result.mime_type == ExportService.MIME_PDF
        assert result.path is not None
        assert result.path.endswith(".pdf")

    def test_export_unsupported_extension(self, export_service):
        with pytest.raises(ExportError, match="(?i)unsupported"):
            export_service.export("data.xyz", SAMPLE_HEADERS, SAMPLE_ROWS)


# Error handling


class TestErrorHandling:
    def test_invalid_path_raises_export_error(self):
        """Writing to a non-existent directory without auto_create."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_dir = os.path.join(tmpdir, "does_not_exist", "nested")
            svc = ExportService(export_dir=bad_dir, auto_create=False)
            with pytest.raises(ExportError, match="Could not write"):
                svc.to_csv("test.csv", SAMPLE_HEADERS, SAMPLE_ROWS)

    def test_excel_invalid_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_dir = os.path.join(tmpdir, "missing")
            svc = ExportService(export_dir=bad_dir, auto_create=False)
            with pytest.raises(ExportError, match="Could not write Excel"):
                svc.to_excel("test.xlsx", SAMPLE_HEADERS, SAMPLE_ROWS)


# Integration: test_ui_flow.py reference still works


def test_export_service_importable():
    """Verify the ExportService class can still be imported from the same path."""
    from services.export_service import ExportService as ES

    assert ES is ExportService
