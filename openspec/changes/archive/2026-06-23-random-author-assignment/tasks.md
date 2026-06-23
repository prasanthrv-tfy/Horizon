## 1. Config

- [x] 1.1 Add `authors_collection_id: str = ""` to `PublisherConfig` in `src/blog/models.py`
- [x] 1.2 Add `author_field: str = "author"` to `PublisherConfig` in `src/blog/models.py`

## 2. WebflowPublisher

- [x] 2.1 Add `author_field: str = "author"` parameter to `WebflowPublisher.__init__`; store as `self._author_field`
- [x] 2.2 Add `list_authors(authors_collection_id: str) -> List[Dict[str, Any]]` method that paginates over `/collections/{authors_collection_id}/items` and returns all items (reuse `_PAGE_LIMIT`; fail open on error — return empty list and log warning)
- [x] 2.3 In `add_draft`, read `item.get("author_id")`; if present, set `field_data[self._author_field] = author_id`

## 3. Publisher runner

- [x] 3.1 In `runner.py`, after constructing `WebflowPublisher`, fetch authors: if `authors_collection_id` is set, call `publisher.list_authors(authors_collection_id)`; store as `authors` list (empty list if not configured or fetch fails)
- [x] 3.2 Pass `author_field` from config when constructing `WebflowPublisher`
- [x] 3.3 Per post, before calling `add_draft`: if `authors` is non-empty, set `post["author_id"] = random.choice(authors)["id"]`

## 4. Config file

- [x] 4.1 Document `authors_collection_id` and `author_field` keys in `data/config.json` (add as empty string placeholders so the shape is visible)
