from langchain_core.tools import tool

from app.tools.scrapers.base import fetch_html


def _parse_oxymed_detail(soup) -> dict:
    props = {}
    for item in soup.select(".product-prop__item"):
        name_el = item.select_one(".product-prop__name")
        val_el = item.select_one(".product-prop__value")
        if name_el and val_el:
            props[name_el.get_text(strip=True)] = val_el.get_text(strip=True)

    instructions = {}
    for item in soup.select(".product-instruct__item"):
        name_el = item.select_one(".product-instruct__name")
        desc_el = item.select_one(".product-instruct__desc")
        if name_el and desc_el:
            instructions[name_el.get_text(strip=True)] = desc_el.get_text(strip=True)

    name_el = soup.select_one("h1")
    return {
        "name": name_el.get_text(strip=True) if name_el else None,
        "brand": props.get("Производитель") or props.get("Бренд"),
        "manufacturer": props.get("Производитель"),
        "dosage": props.get("Дозировка"),
        "package_size": props.get("Кол-во в упаковке"),
        "form": props.get("Форма выпуска"),
        "description": instructions.get("Описание"),
        "usage_instructions": instructions.get("Способ применения"),
        "storage_conditions": instructions.get("Особые указания") or instructions.get("Условия хранения"),
    }


def _parse_generic_detail(soup) -> dict:
    name_el = soup.select_one("h1")
    meta_desc = soup.select_one('meta[name="description"]')
    return {
        "name": name_el.get_text(strip=True) if name_el else None,
        "brand": None,
        "manufacturer": None,
        "dosage": None,
        "package_size": None,
        "form": None,
        "description": meta_desc.get("content") if meta_desc else None,
        "usage_instructions": None,
        "storage_conditions": None,
    }


PARSERS = {
    "oxymed.uz": _parse_oxymed_detail,
}


def get_product_details(url: str) -> dict | None:
    soup = fetch_html(url)
    if soup is None:
        return None

    parser = _parse_generic_detail
    for domain, fn in PARSERS.items():
        if domain in url:
            parser = fn
            break

    details = parser(soup)
    details["url"] = url
    return details


@tool
def product_details_tool(url: str) -> dict | None:
    """Fetch detailed information about a single product from its page URL
    (brand, manufacturer, dosage, package size, description, and — if available
    on the site — general usage guidance and storage conditions). Use this after
    a search when the user wants more details about one specific product. This
    tool never gives medical dosing advice — it only reports what the store page
    states.
    """
    return get_product_details(url)
