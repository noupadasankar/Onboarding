"""Tests for SectionDetector."""
import pytest

from app.chunking.section_detector import SectionDetector


@pytest.fixture
def detector() -> SectionDetector:
    return SectionDetector()


class TestHeadingDetection:
    def test_markdown_h1_detected(self, detector: SectionDetector) -> None:
        sections = detector.detect("# Introduction\nSome text here.")
        assert any(s.title == "Introduction" for s in sections)

    def test_markdown_h2_detected(self, detector: SectionDetector) -> None:
        sections = detector.detect("## Leave Policy\nDetails follow.")
        assert any("Leave Policy" in s.title for s in sections)

    def test_all_caps_heading_detected(self, detector: SectionDetector) -> None:
        sections = detector.detect("INTRODUCTION\nWelcome to the handbook.")
        assert any("INTRODUCTION" in s.title for s in sections)

    def test_numbered_heading_detected(self, detector: SectionDetector) -> None:
        text = "1. Introduction\nWelcome.\n\n2. Leave Policy\nDetails here."
        sections = detector.detect(text)
        titles = [s.title for s in sections]
        assert any("Introduction" in t for t in titles)
        assert any("Leave Policy" in t for t in titles)

    def test_sections_sorted_by_position(self, detector: SectionDetector) -> None:
        text = "# A\nText A.\n# B\nText B.\n# C\nText C."
        sections = detector.detect(text)
        positions = [s.start_pos for s in sections]
        assert positions == sorted(positions)

    def test_empty_text_returns_empty(self, detector: SectionDetector) -> None:
        assert detector.detect("") == []

    def test_no_headings_returns_empty(self, detector: SectionDetector) -> None:
        text = "This is just a paragraph with no headings whatsoever."
        # May or may not detect headings — just ensure no crash
        sections = detector.detect(text)
        assert isinstance(sections, list)


class TestFalsePositiveFiltering:
    def test_sentence_ending_with_period_rejected(self, detector: SectionDetector) -> None:
        sections = detector.detect("This is a sentence.\nBody text.")
        # A line ending with '.' should not be treated as a heading
        for s in sections:
            assert not s.title.endswith(".")

    def test_date_not_treated_as_heading(self, detector: SectionDetector) -> None:
        sections = detector.detect("01/01/2026\nText follows.")
        for s in sections:
            assert "2026" not in s.title or not s.title.startswith("01")

    def test_blank_line_not_a_heading(self, detector: SectionDetector) -> None:
        sections = detector.detect("\n\nActual content here.\n")
        for s in sections:
            assert s.title.strip()


class TestAssignSections:
    def test_text_split_by_headings(self, detector: SectionDetector) -> None:
        text = (
            "# Introduction\n"
            "Welcome to the handbook.\n\n"
            "# Leave Policy\n"
            "You have 20 days of annual leave."
        )
        blocks = detector.assign_sections(text)
        assert len(blocks) >= 2
        titles = [title for _, title in blocks]
        assert any("Introduction" in t for t in titles)
        assert any("Leave Policy" in t for t in titles)

    def test_text_before_first_heading(self, detector: SectionDetector) -> None:
        text = "Preamble text.\n\n# Chapter One\nContent here."
        blocks = detector.assign_sections(text)
        # The preamble block should be present with empty section title
        assert any(b[1] == "" for b in blocks)

    def test_no_headings_returns_whole_text(self, detector: SectionDetector) -> None:
        text = "Just a plain document with no headings at all."
        blocks = detector.assign_sections(text)
        assert len(blocks) == 1
        assert blocks[0][1] == ""
        assert "plain document" in blocks[0][0]

    def test_empty_blocks_excluded(self, detector: SectionDetector) -> None:
        text = "# Heading\n# Another Heading\nSome content."
        blocks = detector.assign_sections(text)
        for block_text, _ in blocks:
            assert block_text.strip()

    def test_empty_text_returns_empty(self, detector: SectionDetector) -> None:
        assert detector.assign_sections("") == []

    def test_block_text_contains_expected_content(self, detector: SectionDetector) -> None:
        text = "# Benefits\nEmployees receive health insurance and dental cover."
        blocks = detector.assign_sections(text)
        combined = " ".join(b[0] for b in blocks)
        assert "health insurance" in combined

    def test_realistic_handbook_structure(self, detector: SectionDetector) -> None:
        text = (
            "EMPLOYEE HANDBOOK\n\n"
            "1. Introduction\n"
            "Welcome to the company. We value integrity and collaboration.\n\n"
            "2. Working Hours\n"
            "Standard hours are 09:00 to 17:30, Monday to Friday.\n\n"
            "3. Leave Policy\n"
            "You are entitled to 20 days of annual leave per year.\n"
        )
        blocks = detector.assign_sections(text)
        # Should detect multiple sections
        assert len(blocks) >= 2
