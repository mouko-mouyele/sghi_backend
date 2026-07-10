from math import ceil

MAX_PAGE_SIZE = 100


def normalize_page_params(page: int = 1, page_size: int = 20) -> tuple[int, int]:
    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    return page, page_size


def paginate_queryset(qs, page: int = 1, page_size: int = 20):
    page, page_size = normalize_page_params(page, page_size)
    total = qs.count()
    offset = (page - 1) * page_size
    items = list(qs[offset:offset + page_size])
    total_pages = ceil(total / page_size) if total else 0
    meta = {
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
    }
    return items, meta


def paginated(items, meta: dict):
    return {'items': items, **meta}
