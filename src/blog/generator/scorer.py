import asyncio
from typing import List

from rich.console import Console

from ...ai.utils import parse_json_response
from ...models import ContentItem
from .loader import _clean_title
from ..models import ScoredItem
from ..profiles.profile import BlogPromptProfile
from .prompts import (
    ITEM_SCORING_SYSTEM,
    ITEM_SCORING_USER,
    RELEVANCE_RANKING_SYSTEM,
    RELEVANCE_RANKING_SYSTEM_DEFAULT_CRITERIA,
    RELEVANCE_RANKING_USER,
)


async def rank_by_relevance(
    items: List[ContentItem], ai_client, console: Console, audience_context: str = ""
) -> List[ContentItem]:
    """Re-rank items by content relevance using AI, optionally scoped to a specific audience."""
    if len(items) <= 1:
        return items

    console.print("🔄 Ranking items by relevance...")

    if audience_context.strip():
        audience_context_block = (
            "Rank for the following specific audience:\n\n"
            f"{audience_context.strip()}\n\n"
            "Given a list of news items (each with a title, summary, tags, and content snippet), "
            "rank them from MOST to LEAST relevant for this audience."
        )
    else:
        audience_context_block = RELEVANCE_RANKING_SYSTEM_DEFAULT_CRITERIA

    system_prompt = RELEVANCE_RANKING_SYSTEM.format(audience_context_block=audience_context_block)

    item_texts = []
    for item in items:
        content_preview = ""
        if item.content:
            content_preview = item.content.split("--- Top Comments ---")[0].strip()[:500]
        item_texts.append(
            f"ID: {item.id}\n"
            f"Title: {item.title}\n"
            f"Summary: {item.ai_summary or item.title}\n"
            f"Tags: {', '.join(item.ai_tags) if item.ai_tags else 'none'}\n"
            f"Content: {content_preview}\n"
        )

    items_text = "\n---\n".join(item_texts)
    user_prompt = RELEVANCE_RANKING_USER.format(
        count=len(items),
        items_text=items_text,
    )

    try:
        response = await ai_client.complete(
            system=system_prompt,
            user=user_prompt,
            temperature=0.3,
        )
        result = parse_json_response(response)
        if result and "ranked_ids" in result:
            id_to_item = {item.id: item for item in items}
            ranked = []
            for item_id in result["ranked_ids"]:
                if item_id in id_to_item:
                    ranked.append(id_to_item.pop(item_id))
            ranked.extend(id_to_item.values())
            return ranked
    except Exception as e:
        console.print(f"[yellow]⚠️  Relevance ranking failed ({e}), using original order[/yellow]")

    return items


def _compute_weighted_sum(dim_scores: dict, gate_path) -> float:
    total = 0.0
    for pdc in gate_path.dimensions:
        score = dim_scores.get(pdc.dimension, {}).get("score", 0)
        total += pdc.weight * score
    return round(total, 3)


async def _score_single_item(
    item: ContentItem,
    dimensions_text: str,
    ai_client,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Score one item on all dimensions. Returns a dimensions dict or {} on failure."""
    content_preview = ""
    if item.content:
        content_preview = item.content.split("--- Top Comments ---")[0].strip()[:1500]
    item_text = (
        f"ID: {item.id}\nTitle: {item.title}\nSummary: {item.ai_summary or item.title}\n"
        f"Tags: {', '.join(item.ai_tags or [])}\nContent: {content_preview}"
    )
    user_prompt = ITEM_SCORING_USER.format(
        count=1,
        dimensions_text=dimensions_text,
        items_text=item_text,
    )
    async with semaphore:
        try:
            response = await ai_client.complete(
                system=ITEM_SCORING_SYSTEM,
                user=user_prompt,
                temperature=0.1,
            )
            result = parse_json_response(response)
            if result and "items" in result and result["items"]:
                return result["items"][0].get("dimensions", {})
        except Exception:
            pass
    return {}


async def score_items_for_profile(
    items: List[ContentItem],
    ai_client,
    console: Console,
    profile: BlogPromptProfile,
) -> List[ScoredItem]:
    """Score items on profile dimensions, apply gate paths, return ScoredItem list."""
    dims = profile.scoring_dimensions
    gate_paths = profile.gate_paths
    dim_map = {d.name: d for d in dims}

    # Build dimension definitions for the prompt (shared across all calls)
    dim_lines = []
    for d in dims:
        anchor_text = " | ".join(f"{k}={v}" for k, v in sorted(d.anchors.items(), key=lambda x: int(x[0])))
        dim_lines.append(f"**{d.name}**: {d.description}\n  Anchors: {anchor_text}")
    dimensions_text = "\n\n".join(dim_lines)

    console.print(f"🔬 [{profile.name}] Scoring {len(items)} items on {len(dims)} dimensions...")

    concurrency = getattr(ai_client, "config", None)
    concurrency = getattr(concurrency, "analysis_concurrency", 5) if concurrency else 5
    semaphore = asyncio.Semaphore(concurrency)

    dimension_scores_list = await asyncio.gather(
        *[_score_single_item(item, dimensions_text, ai_client, semaphore) for item in items]
    )
    raw_scores = {item.id: dim_scores for item, dim_scores in zip(items, dimension_scores_list)}

    scored_items: List[ScoredItem] = []
    for item in items:
        dim_scores = raw_scores.get(item.id, {})

        # Evaluate each gate path
        path_results: dict = {}
        for gate_path in gate_paths:
            passed = True
            failed: List[str] = []
            scores_snapshot = {}
            for pdc in gate_path.dimensions:
                score = dim_scores.get(pdc.dimension, {}).get("score", 0)
                scores_snapshot[pdc.dimension] = score
                if score < pdc.threshold:
                    passed = False
                    failed.append(pdc.dimension)
            path_results[gate_path.name] = {"passed": passed, "scores": scores_snapshot, "failed_gates": failed}

        # Determine inclusion (first passing path wins)
        inclusion_path = None
        failed_gates: dict = {}
        for gate_path in gate_paths:
            pr = path_results[gate_path.name]
            if pr["passed"]:
                inclusion_path = gate_path.name
                break
            else:
                failed_gates[gate_path.name] = pr["failed_gates"]
        included = inclusion_path is not None

        # Compute weighted sum from the winning path's dimension configs
        weighted_sum = 0.0
        if included:
            winning_path = next(gp for gp in gate_paths if gp.name == inclusion_path)
            weighted_sum = _compute_weighted_sum(dim_scores, winning_path)
        else:
            # Best possible sum across all paths for ranking/logging even when excluded
            sums = [_compute_weighted_sum(dim_scores, gp) for gp in gate_paths]
            weighted_sum = max(sums) if sums else 0.0

        scored_items.append(ScoredItem(
            item=item,
            dimension_scores=dim_scores,
            path_results=path_results,
            included=included,
            inclusion_path=inclusion_path,
            failed_gates=failed_gates,
            weighted_sum=weighted_sum,
        ))

    # Console table
    dim_names = [d.name for d in dims]
    col_w = 6
    header = f"  {'#':>3}  {'Title':<35}" + "".join(f" {n[:col_w]:>{col_w}}" for n in dim_names) + f" {'wsum':>6}  decision"
    console.print(f"\n{header}")
    console.print("  " + "-" * (len(header) - 2))
    for row_num, si in enumerate(scored_items, 1):
        title = _clean_title(si.item.title)[:34]
        scores_str = "".join(
            f" {str(si.dimension_scores.get(n, {}).get('score', '?')):>{col_w}}"
            for n in dim_names
        )
        wsum_str = f" {si.weighted_sum:>6.2f}"
        if si.included:
            decision = f"[green]✓ {si.inclusion_path}[/green]"
        else:
            all_failed = [g for gs in si.failed_gates.values() for g in gs]
            decision = f"[red]✗ ({', '.join(dict.fromkeys(all_failed))})[/red]"
        console.print(f"  {row_num:>3}  {title:<35}{scores_str}{wsum_str}  {decision}")
    console.print()

    included_count = sum(1 for si in scored_items if si.included)
    console.print(f"🏆 [{profile.name}] {included_count}/{len(scored_items)} items passed the gates\n")

    return scored_items
