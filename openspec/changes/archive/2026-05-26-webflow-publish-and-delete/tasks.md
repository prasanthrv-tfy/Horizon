## 1. Implement publish_draft

- [x] 1.1 Replace the `NotImplementedError` stub in `WebflowPublisher.publish_draft` with a `POST /collections/{collection_id}/items/publish` call using `{"itemIds": [item_id]}`
- [x] 1.2 Check the 202 response: raise `RuntimeError` if `item_id` is absent from `publishedItemIds` or present in `errors`
- [x] 1.3 Raise `RuntimeError` on any non-2xx response, including status code and response body

## 2. Implement delete_item

- [x] 2.1 Replace the `NotImplementedError` stub in `WebflowPublisher.delete_item` with a `DELETE /collections/{collection_id}/items` call using `{"items": [{"id": item_id}]}`
- [x] 2.2 Call `raise_for_status()` to raise on non-2xx responses

## 3. Update spec

- [x] 3.1 Merge the `blog-publisher-interface` delta spec into `openspec/specs/blog-publisher-interface/spec.md` — update the `WebflowPublisher implementation` requirement to reflect both methods are now fully implemented (not stubs)
