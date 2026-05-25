"""horizon-blog CLI: reads pipeline output and generates blog posts.

Input file is fixed at data/pipeline-output/important_items.json.
Run `uv run horizon` first to produce that file, then `uv run horizon-blog`.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from rich.console import Console

from ..ai.client import create_ai_client
from ..ai.utils import parse_json_response
from ..models import Config, ContentItem
from ..storage.manager import StorageManager
from .models import BlogConfig, BlogPost, ScoredItem
from .profiles import PROFILES
from .profiles.profile import BlogPromptProfile
from .prompts import ITEM_SCORING_SYSTEM, ITEM_SCORING_USER, RELEVANCE_RANKING_SYSTEM, RELEVANCE_RANKING_SYSTEM_DEFAULT_CRITERIA, RELEVANCE_RANKING_USER
from .fetcher import ContentFetcher
from .writer import BlogWriter

# Fixed input path — run `uv run horizon` to refresh this file
IMPORTANT_ITEMS_PATH = Path("artifacts/pipeline-output/important_items.json")
THIN_CONTENT_THRESHOLD = 500


def load_important_items(path: Path) -> List[ContentItem]:
    if not path.exists():
        print(
            f"[error] {path} not found. Run `uv run horizon` first to generate it.",
            file=sys.stderr,
        )
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    if not data:
        print("No items in pipeline output. Nothing to do.", file=sys.stderr)
        sys.exit(0)

    return [ContentItem(**item) for item in data]


def resolve_profiles(name: str) -> List[BlogPromptProfile]:
    """Return the list of profiles to run for the given profile name."""
    if name == "all":
        return list(PROFILES.values())
    if name not in PROFILES:
        available = ", ".join(PROFILES.keys())
        print(
            f"[error] Unknown prompt_profile '{name}'. Available profiles: {available}",
            file=sys.stderr,
        )
        sys.exit(1)
    return [PROFILES[name]]


async def _enrich_one(
    item,
    fetcher: ContentFetcher,
    semaphore: asyncio.Semaphore,
    console: Console,
) -> None:
    async with semaphore:
        try:
            text = await fetcher.fetch_url(str(item.url))
            item.content = text
            console.print(f"   [green]✓ fetched[/green] {str(item.url)[:70]}")
            return
        except Exception as fetch_err:
            console.print(
                f"   [yellow]⚠ fetch failed ({fetch_err.__class__.__name__}), using search for:[/yellow] {item.title[:60]}"
            )

        text = fetcher.search_fallback(item.title, item.ai_tags or [])
        if text.strip():
            item.content = text
        else:
            console.print(f"   [red]✗ enrichment failed for:[/red] {item.title[:60]}")


async def enrich_thin_items(items: List[ContentItem], console: Console) -> None:
    """Fetch or search-enrich items whose content is below THIN_CONTENT_THRESHOLD."""
    thin = [it for it in items if len(it.content or "") < THIN_CONTENT_THRESHOLD]
    if not thin:
        return

    console.print(f"🔍 Enriching {len(thin)} thin-content items before scoring...")
    semaphore = asyncio.Semaphore(5)
    async with ContentFetcher() as fetcher:
        await asyncio.gather(*[_enrich_one(it, fetcher, semaphore, console) for it in thin])
    console.print()


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
        title = si.item.title[:34]
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


def _write_ranking_results(
    profiles_scored: dict,
    items_total: int,
    max_posts: int,
) -> None:
    """Regenerate ranking_results.md from the current run's scoring data."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    profile_names = ", ".join(profiles_scored.keys())
    lines: List[str] = []

    lines.append(f"# Ranking Results — {today}\n")
    lines.append(f"**Items evaluated:** {items_total}  ")
    lines.append(f"**Profiles run:** {profile_names}\n")
    lines.append(
        "> This file is auto-generated at the end of each `horizon-blog` run. "
        "Profile and gate descriptions live in [`docs/blog-profiles.md`](docs/blog-profiles.md).\n"
    )
    lines.append("---\n")
    lines.append("## Results\n")

    for profile, scored in profiles_scored.values():
        dims = profile.scoring_dimensions
        dim_names = [d.name for d in dims]
        passed_count = sum(1 for si in scored if si.included)
        total_count = len(scored)

        # Short abbreviations: first 4 chars of each dimension name
        abbrevs = {d.name: d.name[:4] for d in dims}
        legend = " · ".join(f"`{abbrevs[n]}` = {n}" for n in dim_names)

        lines.append(f"### {profile.name.capitalize()} — {passed_count} / {total_count} items passed\n")
        if legend:
            lines.append(legend + "  \n")
            lines.append(
                "WSum for passed items uses the winning path formula. "
                "WSum for failed items = max across paths for reference.\n"
            )

        # Build header row
        abbrev_cols = " | ".join(f"{abbrevs[n]}" for n in dim_names)
        lines.append(f"| # | Title | {abbrev_cols} | WSum | Decision |")
        lines.append("|" + "|".join(["---"] * (len(dim_names) + 4)) + "|")

        # Determine top-max_posts included items by weighted_sum for star markers
        top_included = sorted(
            [si for si in scored if si.included],
            key=lambda si: si.weighted_sum,
            reverse=True,
        )[:max_posts]
        top_ids = {si.item.id for si in top_included}

        for row_num, si in enumerate(scored, 1):
            title = si.item.title.replace("|", "\\|")
            color = "green" if si.included else "red"
            scores_cols = " | ".join(
                str(si.dimension_scores.get(n, {}).get("score", "?")) for n in dim_names
            )
            wsum = f"**{si.weighted_sum:.2f}**" if si.included else f"{si.weighted_sum:.2f}"

            if si.included:
                star = " ⭐" if si.item.id in top_ids else ""
                decision = f"✓ {si.inclusion_path}{star}"
            else:
                all_failed = list(dict.fromkeys(g for gs in si.failed_gates.values() for g in gs))
                decision = "✗ " + ", ".join(all_failed)

            lines.append(
                f"| {row_num} | <span style=\"color:{color}\">{title}</span> "
                f"| {scores_cols} | {wsum} | {decision} |"
            )

        lines.append("")

        # Top N selected table
        has_multiple_paths = len(profile.gate_paths) > 1
        if top_included:
            lines.append(f"#### Top {len(top_included)} selected\n")
            if has_multiple_paths:
                lines.append("| Rank | Title | Path | WSum |")
                lines.append("|---|---|---|---|")
                for rank, si in enumerate(top_included, 1):
                    lines.append(f"| {rank} | {si.item.title} | {si.inclusion_path} | {si.weighted_sum:.2f} |")
            else:
                lines.append("| Rank | Title | WSum |")
                lines.append("|---|---|---|")
                for rank, si in enumerate(top_included, 1):
                    lines.append(f"| {rank} | {si.item.title} | {si.weighted_sum:.2f} |")
            lines.append("")

        lines.append("---\n")

    # Cross-profile comparison (only when ≥2 profiles were scored)
    if len(profiles_scored) >= 2:
        profile_list = list(profiles_scored.values())
        lines.append("## Profile Comparison\n")

        # Summary table
        header_cols = " | ".join(p.name.capitalize() for p, _ in profile_list)
        lines.append(f"| Metric | {header_cols} |")
        lines.append("|" + "|".join(["---"] * (len(profile_list) + 1)) + "|")

        def _row(label, fn):
            vals = " | ".join(str(fn(p, s)) for p, s in profile_list)
            return f"| {label} | {vals} |"

        lines.append(_row("Items evaluated", lambda p, s: len(s)))
        lines.append(_row(
            "Items passed gate(s)",
            lambda p, s: f"**{sum(1 for si in s if si.included)}** ({sum(1 for si in s if si.included) * 100 // len(s)}%)",
        ))
        lines.append(_row("Items excluded", lambda p, s: sum(1 for si in s if not si.included)))
        lines.append(_row("Gate paths", lambda p, s: len(p.gate_paths)))
        lines.append(_row(
            "Top item",
            lambda p, s: (
                lambda top: f"{top.item.title} ({top.weighted_sum:.2f})" if top else "—"
            )(next(iter(sorted([si for si in s if si.included], key=lambda x: x.weighted_sum, reverse=True)), None)),
        ))
        lines.append("")

        # Build lookup: item_id -> {profile_name: ScoredItem}
        all_ids_ordered: List[str] = []
        seen: set = set()
        for _, scored in profile_list:
            for si in scored:
                if si.item.id not in seen:
                    all_ids_ordered.append(si.item.id)
                    seen.add(si.item.id)

        id_to_si: dict = {}
        for p, scored in profile_list:
            for si in scored:
                id_to_si.setdefault(si.item.id, {})[p.name] = si

        # Items passing ALL profiles
        passing_all = [
            iid for iid in all_ids_ordered
            if all(id_to_si[iid].get(p.name, None) and id_to_si[iid][p.name].included for p, _ in profile_list)
        ]
        if passing_all:
            lines.append(f"### Items passing all profiles ({len(passing_all)})\n")
            wsums_header = " | ".join(f"{p.name.capitalize()} WSum" for p, _ in profile_list)
            path_header = " | ".join(f"{p.name.capitalize()} Path" for p, _ in profile_list)
            lines.append(f"| Title | {wsums_header} | {path_header} |")
            lines.append("|" + "|".join(["---"] * (1 + len(profile_list) * 2)) + "|")
            for iid in passing_all:
                title = id_to_si[iid][profile_list[0][0].name].item.title
                wsums = " | ".join(f"{id_to_si[iid][p.name].weighted_sum:.2f}" for p, _ in profile_list)
                paths = " | ".join(id_to_si[iid][p.name].inclusion_path or "—" for p, _ in profile_list)
                lines.append(f"| {title} | {wsums} | {paths} |")
            lines.append("")

        # Items passing some but not all profiles
        for p_focus, s_focus in profile_list:
            other_profiles = [(p, s) for p, s in profile_list if p.name != p_focus.name]
            exclusive = [
                iid for iid in all_ids_ordered
                if id_to_si.get(iid, {}).get(p_focus.name) and id_to_si[iid][p_focus.name].included
                and any(
                    not (id_to_si.get(iid, {}).get(p.name) and id_to_si[iid][p.name].included)
                    for p, _ in other_profiles
                )
            ]
            if exclusive:
                other_names = " and ".join(p.name for p, _ in other_profiles)
                lines.append(f"### Items passing {p_focus.name} but NOT {other_names} ({len(exclusive)})\n")
                excl_reason_headers = " | ".join(f"{p.name.capitalize()} exclusion" for p, _ in other_profiles)
                lines.append(f"| Title | {p_focus.name.capitalize()} WSum | Path | {excl_reason_headers} |")
                lines.append("|" + "|".join(["---"] * (3 + len(other_profiles))) + "|")
                for iid in exclusive:
                    si_f = id_to_si[iid][p_focus.name]
                    title = si_f.item.title
                    excl_reasons = []
                    for p_other, _ in other_profiles:
                        si_other = id_to_si.get(iid, {}).get(p_other.name)
                        if si_other and not si_other.included:
                            failed = list(dict.fromkeys(g for gs in si_other.failed_gates.values() for g in gs))
                            excl_reasons.append("Low " + ", ".join(failed) if failed else "excluded")
                        else:
                            excl_reasons.append("not scored")
                    lines.append(
                        f"| {title} | {si_f.weighted_sum:.2f} | {si_f.inclusion_path} | "
                        + " | ".join(excl_reasons) + " |"
                    )
                lines.append("")

    out = Path("artifacts/ranking_results.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def _write_run_log(scored_items: List[ScoredItem], profile_name: str) -> None:
    """Persist full scoring details to data/blog-runs/YYYY-MM-DD-{profile}.json."""
    log_dir = Path("artifacts/blog-runs")
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    log_path = log_dir / f"{today}-{profile_name}.json"

    results = []
    for idx, si in enumerate(scored_items, 1):
        results.append({
            "row": idx,
            "id": si.item.id,
            "title": si.item.title,
            "included": si.included,
            "inclusion_path": si.inclusion_path,
            "weighted_sum": si.weighted_sum,
            "dimensions": si.dimension_scores,
            "path_results": si.path_results,
            "failed_gates": si.failed_gates,
        })

    log_data = {
        "profile": profile_name,
        "run_at": datetime.utcnow().isoformat() + "Z",
        "items_evaluated": len(scored_items),
        "items_included": sum(1 for si in scored_items if si.included),
        "items_excluded": sum(1 for si in scored_items if not si.included),
        "results": results,
    }
    log_path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False), encoding="utf-8")
    console_path = f"data/blog-runs/{today}-{profile_name}.json"
    return console_path


async def generate_and_save_posts(
    items: List[ContentItem],
    config: Config,
    profile: BlogPromptProfile,
    console: Console,
) -> None:
    """Generate blog posts for one profile and write them to disk."""
    if not items:
        console.print("[yellow]No items to process — skipping blog generation.[/yellow]")
        return

    blog_cfg = config.blog or BlogConfig()
    ai_client = create_ai_client(config.ai)
    writer = BlogWriter(
        ai_client,
        profile=profile,
        audience_context=blog_cfg.audience_context,
        platform_context=blog_cfg.platform_context,
    )
    languages = list(config.ai.languages)

    console.print(
        f"📝 [{profile.name}] Generating blog posts for {len(items)} items in {languages}..."
    )
    posts_by_lang = await writer.generate_blog_posts(items, languages)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    # Profile-scoped output directory for side-by-side comparison
    archive_dir = Path(blog_cfg.output_dir) / profile.name

    for lang, posts in posts_by_lang.items():
        for post in posts:
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / f"{today}-{post.slug}-{lang}.md"
            archive_path.write_text(post.markdown, encoding="utf-8")

            jekyll_dir = Path("docs/_posts") / profile.name
            jekyll_dir.mkdir(parents=True, exist_ok=True)
            jekyll_path = jekyll_dir / f"{today}-{post.slug}-{lang}.md"

            front_matter = (
                "---\n"
                "layout: post\n"
                "type: blog\n"
                f"title: \"{post.title.replace(chr(34), chr(39))}\"\n"
                f"date: {today}\n"
                f"lang: {lang}\n"
                f"profile: {profile.name}\n"
                f"score: {post.score}\n"
                f"original_url: \"{post.url}\"\n"
                f"tags: [{', '.join(post.tags)}]\n"
                "---\n\n"
            )

            content = post.markdown
            first_line = content.strip().split("\n")[0]
            if first_line.startswith("# "):
                parts = content.split("\n", 1)
                if len(parts) > 1:
                    content = parts[1].strip()

            jekyll_path.write_text(front_matter + content, encoding="utf-8")

        console.print(
            f"   {lang.upper()}: {len(posts)} posts → {archive_dir}/ and docs/_posts/{profile.name}/"
        )

    total = sum(len(p) for p in posts_by_lang.values())
    console.print(f"   Total: {total} blog posts generated\n")


async def _run(profile_arg: str | None, rank_only: bool = False, items_arg: str | None = None, all_posts: bool = False) -> None:
    load_dotenv()
    console = Console()
    mode_label = "Ranking only" if rank_only else "Starting blog generation"
    console.print(f"[bold cyan]📝 Horizon Blog — {mode_label}...[/bold cyan]\n")

    storage = StorageManager()
    config = storage.load_config()

    items = load_important_items(IMPORTANT_ITEMS_PATH)
    console.print(f"📥 Loaded {len(items)} items from {IMPORTANT_ITEMS_PATH}\n")

    pinned_items = None
    if items_arg:
        try:
            row_nums = [int(n.strip()) for n in items_arg.split(",") if n.strip()]
        except ValueError:
            console.print("[red]✗ --items expects comma-separated integers (e.g. --items 3,7,15)[/red]")
            sys.exit(1)
        invalid = [n for n in row_nums if n < 1 or n > len(items)]
        if invalid:
            console.print(f"[red]✗ Row numbers out of range (1–{len(items)}): {invalid}[/red]")
            sys.exit(1)
        pinned_items = [items[n - 1] for n in row_nums]
        console.print(f"🎯 Pinned {len(pinned_items)} item(s) by row number — skipping scoring gates.\n")
        for n, it in zip(row_nums, pinned_items):
            console.print(f"   {n}. {it.title}")
        console.print()

    blog_cfg = config.blog or BlogConfig()
    max_posts = None if all_posts else blog_cfg.max_posts

    ai_client = create_ai_client(config.ai)

    await enrich_thin_items(items, console)

    profile_name = profile_arg or blog_cfg.prompt_profile
    profiles = resolve_profiles(profile_name)
    profiles_scored: dict = {}
    for profile in profiles:
        if pinned_items is not None:
            selected = pinned_items
        elif profile.scoring_dimensions:
            scored = await score_items_for_profile(items, ai_client, console, profile)
            log_path = _write_run_log(scored, profile.name)
            console.print(f"📋 Run log → {log_path}\n")
            profiles_scored[profile.name] = (profile, scored)
            included = sorted(
                (si for si in scored if si.included),
                key=lambda si: si.weighted_sum,
                reverse=True,
            )
            selected = [si.item for si in (included if max_posts is None else included[:max_posts])]
            if not selected:
                console.print(f"[yellow]⚠️  [{profile.name}] No items passed the gates — skipping post generation.[/yellow]\n")
                continue
        else:
            ranked = await rank_by_relevance(items, ai_client, console, profile.ranking_context)
            selected = ranked if max_posts is None else ranked[:max_posts]

        console.print(f"🏆  [{profile.name}] Selected top {len(selected)} items:")
        for i, item in enumerate(selected, 1):
            console.print(f"   {i}. {item.title}")
        console.print()

        if rank_only:
            continue

        await generate_and_save_posts(selected, config, profile, console)

    if profiles_scored:
        _write_ranking_results(profiles_scored, len(items), max_posts)
        console.print("📊 ranking_results.md updated\n")


def main() -> None:
    available = ", ".join(PROFILES.keys())
    parser = argparse.ArgumentParser(description="Generate blog posts from Horizon pipeline output.")
    parser.add_argument(
        "--profile",
        metavar="PROFILE",
        help=f"Prompt profile to use: {available}, or 'all'. Overrides config.json.",
    )
    parser.add_argument(
        "--rank-only",
        action="store_true",
        help="Score and rank items but skip blog post generation.",
    )
    parser.add_argument(
        "--items",
        metavar="ROW_NUMS",
        help="Comma-separated 1-based row numbers of items to generate posts for directly, bypassing scoring gates. Row numbers are shown in the scoring table (run with --rank-only first to see them).",
    )
    parser.add_argument(
        "--all-posts",
        action="store_true",
        help="Generate blog posts for all items that passed the gates, ignoring the max_posts limit in config.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.profile, rank_only=args.rank_only, items_arg=args.items, all_posts=args.all_posts))
