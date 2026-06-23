## 1. Config

- [x] 1.1 Add `categories_collection_id: str = ""` to `PublisherConfig` in `src/blog/models.py`
- [x] 1.2 Add `category_field: str = "category-2"` to `PublisherConfig` in `src/blog/models.py`

## 2. Category module

- [x] 2.1 Create `src/blog/publisher/category.py` with `assign_category(title, tags, categories, ai_client) -> Optional[str]`
- [x] 2.2 Prompt: system prompt instructs LLM to return `{"category": "<name>"}` given title, tags, and category name list
- [x] 2.3 Parse JSON response; look up returned name in name → ID map; return ID or None on any failure (fail open, log warning)

## 3. WebflowPublisher

- [x] 3.1 Add `category_field: str = "category-2"` parameter to `WebflowPublisher.__init__`; store as `self._category_field`
- [x] 3.2 Add `list_categories(categories_collection_id: str) -> List[Dict[str, Any]]` method — same pagination pattern as `list_authors`
- [x] 3.3 In `add_draft`, read `item.get("category_id")`; if present, set `field_data[self._category_field] = category_id`

## 4. Publisher factory and runner

- [x] 4.1 Pass `category_field` from config in `create_publisher()` in `src/blog/publisher/__init__.py`
- [x] 4.2 In `runner.py`, fetch categories once at run start if `categories_collection_id` is set; warn and continue if empty or failed
- [x] 4.3 Per post, call `assign_category(title, tags, categories, ai_client)`; set `post["category_id"]` if a match is returned

## 5. Config file

- [x] 5.1 Add `categories_collection_id: ""` and `category_field: "category-2"` placeholder keys to `data/config.json` under `publisher`