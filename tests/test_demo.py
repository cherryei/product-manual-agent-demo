from app.services.answer_engine import answer_question
from app.services.embedding import embed_text
from app.services.language import detect_language
from app.services.pdf_manual import generate_manual_pdf
from app.services.products import get_product, load_products, match_product_id, product_chunks


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
