import pytest

from app.schemas import FormRequest
from app.stages.ingest import ingest


async def test_name_and_company():
    form = FormRequest(name="Sam Altman", company="OpenAI")
    brief, sources = await ingest(form)

    assert brief.name == "Sam Altman"
    assert brief.company == "OpenAI"
    assert brief.display_name == "Sam Altman"
    assert "Sam Altman" in brief.search_terms
    assert "OpenAI" in brief.search_terms
    assert sources == []


async def test_name_only():
    form = FormRequest(name="Sam Altman")
    brief, sources = await ingest(form)

    assert brief.name == "Sam Altman"
    assert brief.company is None
    assert brief.search_terms == ["Sam Altman"]


async def test_linkedin_url_derives_display_name():
    form = FormRequest(linkedin_url="https://www.linkedin.com/in/satya-nadella")
    brief, sources = await ingest(form)

    assert brief.name is None
    assert brief.display_name == "Satya Nadella"
    assert "Satya Nadella" in brief.search_terms


async def test_name_strips_whitespace():
    form = FormRequest(name="  Sam Altman  ")
    brief, _ = await ingest(form)

    assert brief.name == "Sam Altman"
    assert brief.display_name == "Sam Altman"


async def test_sources_always_empty():
    form = FormRequest(name="Anyone")
    _, sources = await ingest(form)
    assert sources == []
