from __future__ import annotations

from app.schemas import Brief, FormRequest, Source


async def ingest(form: FormRequest) -> tuple[Brief, list[Source]]:
    """Stage 1: Normalise form input into a Brief.

    Pure transformation — no external I/O.  Always returns an empty source
    list (the Brief itself is not a retrieved source).
    """
    name = (form.name or "").strip() or None
    linkedin_url = (form.linkedin_url or "").strip() or None
    company = (form.company or "").strip() or None

    # Best human label for display / query construction.
    if name:
        display_name = name
    elif linkedin_url:
        # e.g. https://www.linkedin.com/in/satya-nadella → "Satya Nadella"
        slug = linkedin_url.rstrip("/").split("/")[-1]
        display_name = slug.replace("-", " ").title()
    else:
        display_name = "Unknown person"

    # Seed terms for Exa queries — name + company give the best signal.
    search_terms: list[str] = []
    if name:
        search_terms.append(name)
    elif display_name != "Unknown person":
        search_terms.append(display_name)
    if company:
        search_terms.append(company)

    return (
        Brief(
            name=name,
            linkedin_url=linkedin_url,
            company=company,
            display_name=display_name,
            search_terms=search_terms,
        ),
        [],  # no sources at this stage
    )
