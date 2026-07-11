"""Tests for TextCleaner."""
import pytest

from app.chunking.cleaner import TextCleaner


@pytest.fixture
def cleaner() -> TextCleaner:
    return TextCleaner()


class TestLineEndingNormalisation:
    def test_crlf_converted_to_lf(self, cleaner: TextCleaner) -> None:
        assert "\r\n" not in cleaner.clean("line one\r\nline two")

    def test_cr_converted_to_lf(self, cleaner: TextCleaner) -> None:
        assert "\r" not in cleaner.clean("line one\rline two")

    def test_lf_preserved(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("line one\nline two")
        assert "line one" in result
        assert "line two" in result


class TestInvisibleCharacterRemoval:
    def test_null_byte_removed(self, cleaner: TextCleaner) -> None:
        assert "\x00" not in cleaner.clean("hello\x00world")

    def test_zero_width_space_removed(self, cleaner: TextCleaner) -> None:
        # U+200B zero-width space
        assert "​" not in cleaner.clean("hello​world")

    def test_bom_removed(self, cleaner: TextCleaner) -> None:
        assert "﻿" not in cleaner.clean("﻿Hello")

    def test_regular_text_preserved(self, cleaner: TextCleaner) -> None:
        text = "Hello, World! This is a normal sentence."
        assert cleaner.clean(text) == text


class TestQuoteNormalisation:
    def test_curly_double_quotes_normalised(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("“Hello”")
        assert '"Hello"' in result

    def test_curly_single_quotes_normalised(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("‘it’s")
        assert "'it's" in result or "it's" in result

    def test_angle_quotes_normalised(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("«Hello»")
        assert '"Hello"' in result


class TestBulletNormalisation:
    def test_bullet_replaced_with_dash(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("• Item one")
        assert result.startswith("-")

    def test_triangular_bullet_replaced(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("‣ Item two")
        assert "-" in result

    def test_black_square_replaced(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("■ Point three")
        assert "-" in result


class TestDashNormalisation:
    def test_en_dash_normalised(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("pages 1–5")
        assert "–" not in result
        assert "-" in result

    def test_em_dash_normalised(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("Note—important")
        assert "—" not in result

    def test_minus_sign_normalised(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("result−negative")
        assert "−" not in result


class TestHyphenBreakJoin:
    def test_hyphenated_line_break_joined(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("hyphen-\nated")
        assert "hyphenated" in result
        assert "-\n" not in result

    def test_normal_hyphen_preserved(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("well-being")
        assert "well-being" in result


class TestRepeatedLineRemoval:
    def test_repeated_header_removed(self, cleaner: TextCleaner) -> None:
        text = "\n".join([
            "ACME CORP CONFIDENTIAL",
            "Chapter 1",
            "ACME CORP CONFIDENTIAL",
            "Chapter 2",
            "ACME CORP CONFIDENTIAL",
        ])
        result = cleaner.clean(text)
        # Should appear at most once
        assert result.count("ACME CORP CONFIDENTIAL") == 1

    def test_rare_line_preserved(self, cleaner: TextCleaner) -> None:
        text = "\n".join([
            "Page header",
            "Some content",
            "More content",
        ])
        # Appears only once → not a repeated header
        result = cleaner.clean(text)
        assert "Page header" in result

    def test_threshold_respected(self) -> None:
        # With threshold=3, a line appearing twice should NOT be removed
        cleaner = TextCleaner(repeated_line_threshold=3)
        text = "Footer\nContent A\nFooter\nContent B"
        result = cleaner.clean(text)
        assert result.count("Footer") == 2


class TestWhitespaceNormalisation:
    def test_multiple_spaces_collapsed(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("hello    world")
        assert "hello world" in result

    def test_tabs_collapsed(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("hello\t\tworld")
        assert "\t" not in result

    def test_multiple_blank_lines_collapsed(self, cleaner: TextCleaner) -> None:
        text = "Para one\n\n\n\n\nPara two"
        result = cleaner.clean(text)
        assert "\n\n\n" not in result

    def test_empty_string_returned_unchanged(self, cleaner: TextCleaner) -> None:
        assert cleaner.clean("") == ""

    def test_whitespace_only_returned_empty(self, cleaner: TextCleaner) -> None:
        assert cleaner.clean("   \n\n\t  ") == ""

    def test_result_stripped(self, cleaner: TextCleaner) -> None:
        result = cleaner.clean("  hello world  ")
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_idempotent(self, cleaner: TextCleaner) -> None:
        text = "Hello, world!\nThis is a test."
        assert cleaner.clean(cleaner.clean(text)) == cleaner.clean(text)
