from pathlib import Path

import pytest

from app.services.answer_engine import answer_question
from app.services.embedding import embed_text
from app.services.language import detect_language
from app.services.pdf_manual import generate_manual_pdf
from app.services.products import get_product, load_products, match_product_id, product_chunks
from app.services.upload_manual import (
    extract_text_from_pdf,
    extract_text_from_txt,
    is_supported_file,
    load_uploaded_manuals,
    process_uploaded_manual,
    save_uploaded_manuals,
    upload_manual,
)


def test_language_detection_defaults_to_english():
    assert detect_language("How do I assemble it?") == "en"


def test_language_detection_japanese():
    assert detect_language("組み立て方法を教えてください") == "jp"


def test_language_detection_chinese():
    assert detect_language("请问这个桌子怎么安装？") == "cn"


def test_product_chunks_exist_for_seven_languages():
    chunks = product_chunks()
    languages = {chunk["language"] for chunk in chunks}
    assert languages == {"en", "de", "it", "fr", "es", "jp", "cn"}


def test_multiple_furniture_products_are_loaded():
    product_ids = {product["id"] for product in load_products()}
    assert {
        "solid-oak-dining-table",
        "five-tier-bookshelf",
        "ergonomic-office-chair",
        "two-door-storage-cabinet",
    }.issubset(product_ids)


def test_embedding_dimension():
    assert len(embed_text("solid wood table")) == 384


def test_answer_question_returns_sources():
    answer, language, product_id, sources = answer_question(
        "How do I assemble the table?",
        product_id="solid-oak-dining-table",
    )
    assert language == "en"
    assert product_id == "solid-oak-dining-table"
    assert "Installation" in answer or "Assembly" in answer
    assert sources


def test_answer_question_auto_matches_bookshelf_in_chinese():
    answer, language, product_id, sources = answer_question("书架怎么安装防倾倒？")
    assert language == "cn"
    assert product_id == "five-tier-bookshelf"
    assert "书架" in answer
    assert sources


def test_answer_question_auto_matches_office_chair_in_english():
    answer, language, product_id, sources = answer_question("How do I install the office chair wheels?")
    assert language == "en"
    assert product_id == "ergonomic-office-chair"
    assert "Office Chair" in answer
    assert sources


def test_answer_question_auto_matches_stool_synonym_in_chinese():
    assert match_product_id("凳子说明书", "cn") == "ergonomic-office-chair"
    answer, language, product_id, sources = answer_question("凳子怎么安装？")
    assert language == "cn"
    assert product_id == "ergonomic-office-chair"
    assert "办公椅" in answer
    assert sources


def test_generate_pdf(tmp_path):
    product = get_product("solid-oak-dining-table")
    assert product["id"] == "solid-oak-dining-table"
    path = generate_manual_pdf(product["id"])
    assert path.exists()
    assert path.stat().st_size > 10_000


# --- Upload manual tests ---

def test_is_supported_file():
    assert is_supported_file("manual.pdf") is True
    assert is_supported_file("manual.txt") is True
    assert is_supported_file("manual.doc") is False
    assert is_supported_file("manual.png") is False
    assert is_supported_file("") is False


# --- helpers for upload tests ---

SAMPLE_TXT = """Product Manual for Smart LED Desk Lamp

Features
- Adjustable brightness and color temperature
- USB charging port
- Flexible gooseneck design
- Touch control panel

Installation
1. Place the lamp base on a flat, dry surface.
2. Connect the USB cable to a 5V/2A adapter.
3. Adjust the gooseneck to your desired angle.
4. Press the touch panel to turn on.

Safety
- Do not immerse in water.
- Unplug before cleaning.
- Use only the provided USB cable.
- Keep away from children under 3 years.

Care
- Wipe with a soft, dry cloth.
- Do not use chemical cleaners.
- Store in a cool, dry place."""


def _create_sample_txt(tmp_path: Path) -> Path:
    path = tmp_path / "test_manual.txt"
    path.write_text(SAMPLE_TXT, encoding="utf-8")
    return path


def _create_sample_pdf(tmp_path: Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    path = tmp_path / "test_manual.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    doc.build([
        Paragraph("Installation Manual", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Step 1: Unpack the box and check all parts.", styles["Normal"]),
        Paragraph("Step 2: Attach the base using the screws provided.", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Safety", styles["Heading1"]),
        Paragraph("Always wear protective gloves during assembly.", styles["Normal"]),
    ])
    return path


def test_extract_text_from_txt(tmp_path):
    path = _create_sample_txt(tmp_path)
    text = extract_text_from_txt(path)
    assert "Smart LED Desk Lamp" in text
    assert "Installation" in text
    assert "Safety" in text
    assert len(text) > 100


def test_extract_text_from_pdf(tmp_path):
    path = _create_sample_pdf(tmp_path)
    text = extract_text_from_pdf(path)
    assert len(text) > 50
    assert "screws" in text.lower() or "assembly" in text.lower()


def test_process_uploaded_manual_txt(tmp_path):
    path = _create_sample_txt(tmp_path)
    product_entry, record = process_uploaded_manual(path, "test_manual.txt")
    assert record["original_filename"] == "test_manual.txt"
    assert product_entry["category"] == "uploaded"
    assert product_entry["id"].startswith("uploaded-")
    langs = product_entry["languages"]
    assert "en" in langs
    assert len(langs["en"]["bullets"]) > 0
    assert record["char_count"] > 100
    assert record["section_count"] >= 1


def test_process_uploaded_manual_pdf(tmp_path):
    path = _create_sample_pdf(tmp_path)
    product_entry, record = process_uploaded_manual(path, "manual.pdf", title="Test Product")
    assert record["title"] == "Test Product"
    assert product_entry["id"].startswith("uploaded-")


def test_save_and_load_uploaded_manuals(tmp_path):
    manuals = [
        {
            "product_id": "test-001",
            "original_filename": "test.txt",
            "file_path": str(tmp_path / "test.txt"),
            "title": "Test",
            "uploaded_at": "2025-01-01T00:00:00",
            "language": "en",
            "char_count": 100,
            "section_count": 3,
        }
    ]
    save_uploaded_manuals(manuals)
    loaded = load_uploaded_manuals()
    assert len(loaded) == 1
    assert loaded[0]["product_id"] == "test-001"


def test_upload_manual_integrates_with_products(tmp_path):
    """Uploading a manual makes it available via load_products()."""
    path = _create_sample_txt(tmp_path)
    result = upload_manual(path, "test_manual.txt", title="LED Lamp")
    product_id = result["product_id"]
    products = load_products()
    ids = [p["id"] for p in products]
    assert product_id in ids, f"Uploaded product {product_id} not found in load_products()"


def test_answer_question_on_uploaded_manual(tmp_path):
    """After uploading a manual, you can ask questions about it."""
    path = _create_sample_txt(tmp_path)
    result = upload_manual(path, "test_manual.txt", title="LED Lamp")
    product_id = result["product_id"]
    answer, language, pid, sources = answer_question(
        "How do I install the lamp?",
        product_id=product_id,
    )
    assert language == "en"
    assert pid == product_id
    assert sources
    assert any("Installation".lower() in source.section.lower() for source in sources)


def test_answer_question_auto_matches_uploaded_manual(tmp_path):
    """The agent should auto-match an uploaded manual by content."""
    path = _create_sample_txt(tmp_path)
    upload_manual(path, "test_manual.txt", title="LED Desk Lamp")
    answer, language, product_id, sources = answer_question(
        "What is the power of the LED desk lamp?"
    )
    assert answer
    assert language == "en"
    assert sources


@pytest.fixture(autouse=True)
def _cleanup_uploaded_manuals():
    """Ensure uploaded manuals are cleaned up after each test."""
    yield
    save_uploaded_manuals([])  # Reset uploaded manuals between tests


# --- Multi-language PDF tests ---

def test_generate_pdf_with_language_subset():
    """PDF generation with a language subset produces only those languages."""
    from app.services.pdf_manual import generate_manual_pdf, resolve_languages
    from app.services.products import get_product

    product = get_product("five-tier-bookshelf")
    selected = resolve_languages(product, ["en", "cn"])
    assert selected == ["en", "cn"]
    path = generate_manual_pdf("five-tier-bookshelf", languages=["en", "cn"])
    assert path.exists()
    assert "en-cn" in path.name
    assert path.stat().st_size > 5_000


def test_generate_pdf_default_all_languages():
    """PDF generation without languages param includes all available languages."""
    from app.services.pdf_manual import generate_manual_pdf, resolve_languages
    from app.services.products import get_product

    product = get_product("solid-oak-dining-table")
    selected = resolve_languages(product, None)
    assert len(selected) == 7
    path = generate_manual_pdf("solid-oak-dining-table")
    assert path.exists()
    assert "en-de-it-fr-es-jp-cn" in path.name


def test_resolve_languages_uploaded_manual_only_has_en():
    """Uploaded manuals now have all 7 languages after auto-translation."""
    from app.services.pdf_manual import resolve_languages

    path = _create_sample_txt(Path("/tmp"))
    result = upload_manual(path, "test.txt", title="Test")
    product_id = result["product_id"]
    product = get_product(product_id)
    # After auto-translation, product should have all 7 languages
    # Request de, fr → should return ['de', 'fr'] (both available now)
    selected = resolve_languages(product, ["de", "fr"])
    assert set(selected) == {"de", "fr"}


# --- Document management tests ---

def test_list_documents():
    """list_documents returns all products with language and deletable flags."""
    from app.services.products import list_documents

    docs = list_documents()
    assert len(docs) >= 4  # at least the 4 built-in products
    for doc in docs:
        assert "id" in doc
        assert "languages" in doc
        assert "deletable" in doc
        assert isinstance(doc["languages"], list)
        if doc["source"] == "builtin":
            assert doc["deletable"] is False
        elif doc["source"] == "uploaded":
            assert doc["deletable"] is True


def test_delete_uploaded_manual():
    """delete_uploaded_manual removes record, file, vectors, and PDFs."""
    from app.services.upload_manual import delete_uploaded_manual

    path = _create_sample_txt(Path("/tmp"))
    result = upload_manual(path, "test.txt", title="Test Lamp")
    product_id = result["product_id"]
    # Generate a PDF so we can verify it gets deleted
    from app.services.pdf_manual import generate_manual_pdf

    pdf_path = generate_manual_pdf(product_id)
    assert pdf_path.exists()
    # Delete
    delete_result = delete_uploaded_manual(product_id)
    assert delete_result["product_id"] == product_id
    assert delete_result["removed_pdfs"] >= 1
    # Verify it's gone
    manuals = load_uploaded_manuals()
    assert not any(m["product_id"] == product_id for m in manuals)
    assert not pdf_path.exists()


def test_delete_builtin_product_raises():
    """Attempting to delete a built-in product raises KeyError."""
    from app.services.upload_manual import delete_uploaded_manual

    with pytest.raises(KeyError):
        delete_uploaded_manual("solid-oak-dining-table")


# --- Translation tests ---

def test_translation_disabled_by_default():
    """Translation is disabled when no LLM is configured."""
    from app.services.translation import is_translation_enabled

    # Without API key, translation should be disabled
    assert is_translation_enabled() is False


def test_batch_translate_fallback_when_disabled():
    """When translation is disabled, all languages get source content."""
    from app.services.translation import batch_translate_sections

    source_sections = {
        "name": "Test Product",
        "summary": "This is a test product.",
        "installation": "Step 1: Unpack. Step 2: Assemble.",
    }

    result = batch_translate_sections(source_sections, "en", ["en", "de", "cn"])

    # All languages should have the same content (no translation)
    assert len(result) == 3
    assert result["en"]["name"] == "Test Product"
    assert result["de"]["name"] == "Test Product"  # Same as source
    assert result["cn"]["name"] == "Test Product"  # Same as source


def test_uploaded_manual_has_all_languages():
    """Uploaded manuals should have 7 languages after processing."""
    from app.services.upload_manual import process_uploaded_manual

    path = _create_sample_txt(Path("/tmp"))
    product_entry, manual_record = process_uploaded_manual(path, "test.txt", title="Test Lamp")

    # Should have all 7 supported languages
    assert len(product_entry["languages"]) == 7
    assert "en" in product_entry["languages"]
    assert "de" in product_entry["languages"]
    assert "cn" in product_entry["languages"]

    # All languages should have the same structure
    for lang, data in product_entry["languages"].items():
        assert "name" in data
        assert "title" in data
        assert "summary" in data
        assert "installation" in data
        assert isinstance(data["installation"], list)
