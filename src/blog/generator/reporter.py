import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .loader import _clean_title
from src.blog.models import BlogPost, ScoredItem
from src.blog.profiles.profile import BlogPromptProfile


def _resolve_title(
    item_id: str,
    raw_title: str,
    ai_title_maps: dict,
    preferred_profile: str | None = None,
) -> str:
    """Return AI-generated headline if available, else raw source title."""
    if preferred_profile and preferred_profile in ai_title_maps:
        title = ai_title_maps[preferred_profile].get(item_id)
        if title:
            return _clean_title(title)
    for title_map in ai_title_maps.values():
        title = title_map.get(item_id)
        if title:
            return _clean_title(title)
    return _clean_title(raw_title)


def _build_header(items_total: int, profiles_scored: dict) -> List[str]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
    return lines


def _build_profile_section(
    profile,
    scored: List[ScoredItem],
    max_posts: int,
    ai_title_maps: dict,
) -> List[str]:
    dimensions = profile.scoring_dimensions
    dim_names = [dim.name for dim in dimensions]
    passed_count = sum(1 for scored_item in scored if scored_item.included)
    total_count = len(scored)
    lines: List[str] = []

    # Short abbreviations: first 4 chars of each dimension name
    abbrevs = {dim.name: dim.name[:4] for dim in dimensions}
    legend = " · ".join(f"`{abbrevs[n]}` = {n}" for n in dim_names)

    lines.append(f"### {profile.name.capitalize()} — {passed_count} / {total_count} items passed\n")
    if legend:
        lines.append(legend + "  \n")
        lines.append(
            "WSum for passed items uses the winning path formula. "
            "WSum for failed items = max across paths for reference.\n"
        )

    abbrev_cols = " | ".join(f"{abbrevs[n]}" for n in dim_names)
    lines.append(f"| # | Title | {abbrev_cols} | WSum | Decision |")
    lines.append("|" + "|".join(["---"] * (len(dim_names) + 4)) + "|")

    # Determine top-max_posts included items by weighted_sum for star markers
    top_included = sorted(
        [scored_item for scored_item in scored if scored_item.included],
        key=lambda scored_item: scored_item.weighted_sum,
        reverse=True,
    )[:max_posts]
    top_ids = {scored_item.item.id for scored_item in top_included}
    row_num_map = {scored_item.item.id: idx for idx, scored_item in enumerate(scored, 1)}

    # Sort all items by WSum descending (passed first, then failed)
    sorted_scored = sorted(scored, key=lambda scored_item: (scored_item.included, scored_item.weighted_sum), reverse=True)

    for scored_item in sorted_scored:
        row_num = row_num_map[scored_item.item.id]
        title = _resolve_title(scored_item.item.id, scored_item.item.title, ai_title_maps, profile.name).replace("|", "\\|")
        color = "green" if scored_item.included else "red"
        scores_cols = " | ".join(
            str(scored_item.dimension_scores.get(n, {}).get("score", "?")) for n in dim_names
        )
        wsum = f"**{scored_item.weighted_sum:.2f}**" if scored_item.included else f"{scored_item.weighted_sum:.2f}"

        if scored_item.included:
            star = " ⭐" if scored_item.item.id in top_ids else ""
            decision = f"✓ {scored_item.inclusion_path}{star}"
        else:
            all_failed = list(dict.fromkeys(g for gs in scored_item.failed_gates.values() for g in gs))
            decision = "✗ " + ", ".join(all_failed)

        lines.append(
            f"| {row_num} | <span style=\"color:{color}\">{title}</span> "
            f"| {scores_cols} | {wsum} | {decision} |"
        )

    lines.append("")

    # Per-path breakdown
    has_multiple_paths = len(profile.gate_paths) > 1
    all_included = sorted(
        [scored_item for scored_item in scored if scored_item.included],
        key=lambda scored_item: scored_item.weighted_sum,
        reverse=True,
    )

    if has_multiple_paths and all_included:
        lines.append("#### By Gate Path\n")
        for gate_path in profile.gate_paths:
            path_items = [scored_item for scored_item in all_included if scored_item.inclusion_path == gate_path.name]
            if not path_items:
                continue
            lines.append(f"**{gate_path.name}** — {len(path_items)} items\n")
            lines.append("| Rank | Title | WSum |")
            lines.append("|---|---|---|")
            for rank, scored_item in enumerate(path_items, 1):
                star = " ⭐" if scored_item.item.id in top_ids else ""
                lines.append(
                    f"| {rank} | {_resolve_title(scored_item.item.id, scored_item.item.title, ai_title_maps, profile.name)}"
                    f"{star} | {scored_item.weighted_sum:.2f} |"
                )
            lines.append("")

    if top_included:
        lines.append(f"#### Top {len(top_included)} selected\n")
        if has_multiple_paths:
            lines.append("| Rank | Title | Path | WSum |")
            lines.append("|---|---|---|---|")
            for rank, scored_item in enumerate(top_included, 1):
                lines.append(
                    f"| {rank} | {_resolve_title(scored_item.item.id, scored_item.item.title, ai_title_maps, profile.name)}"
                    f" | {scored_item.inclusion_path} | {scored_item.weighted_sum:.2f} |"
                )
        else:
            lines.append("| Rank | Title | WSum |")
            lines.append("|---|---|---|")
            for rank, scored_item in enumerate(top_included, 1):
                lines.append(
                    f"| {rank} | {_resolve_title(scored_item.item.id, scored_item.item.title, ai_title_maps, profile.name)}"
                    f" | {scored_item.weighted_sum:.2f} |"
                )
        lines.append("")

    lines.append("---\n")
    return lines


def _build_cross_profile_section(
    profiles_scored: dict,
    ai_title_maps: dict,
) -> List[str]:
    profile_list = list(profiles_scored.values())
    lines: List[str] = []
    lines.append("## Profile Comparison\n")

    # Summary metrics table
    header_cols = " | ".join(p.name.capitalize() for p, _ in profile_list)
    lines.append(f"| Metric | {header_cols} |")
    lines.append("|" + "|".join(["---"] * (len(profile_list) + 1)) + "|")

    def _row(label, fn):
        vals = " | ".join(str(fn(p, s)) for p, s in profile_list)
        return f"| {label} | {vals} |"

    lines.append(_row("Items evaluated", lambda p, s: len(s)))
    lines.append(_row(
        "Items passed gate(s)",
        lambda p, s: f"**{sum(1 for scored_item in s if scored_item.included)}** ({sum(1 for scored_item in s if scored_item.included) * 100 // len(s)}%)",
    ))
    lines.append(_row("Items excluded", lambda p, s: sum(1 for scored_item in s if not scored_item.included)))
    lines.append(_row("Gate paths", lambda p, s: len(p.gate_paths)))
    lines.append(_row(
        "Top item",
        lambda p, s: (
            lambda top: f"{_resolve_title(top.item.id, top.item.title, ai_title_maps, p.name)} ({top.weighted_sum:.2f})" if top else "—"
        )(next(iter(sorted([scored_item for scored_item in s if scored_item.included], key=lambda x: x.weighted_sum, reverse=True)), None)),
    ))
    lines.append("")

    # Build ordered item list and id→ScoredItem lookup across all profiles
    all_ids_ordered: List[str] = []
    seen: set = set()
    for _, scored in profile_list:
        for scored_item in scored:
            if scored_item.item.id not in seen:
                all_ids_ordered.append(scored_item.item.id)
                seen.add(scored_item.item.id)

    item_score_map: dict = {}
    for p, scored in profile_list:
        for scored_item in scored:
            item_score_map.setdefault(scored_item.item.id, {})[p.name] = scored_item

    # Items passing ALL profiles
    passing_all = [
        item_id for item_id in all_ids_ordered
        if all(item_score_map[item_id].get(p.name) and item_score_map[item_id][p.name].included for p, _ in profile_list)
    ]
    if passing_all:
        lines.append(f"### Items passing all profiles ({len(passing_all)})\n")
        wsums_header = " | ".join(f"{p.name.capitalize()} WSum" for p, _ in profile_list)
        path_header = " | ".join(f"{p.name.capitalize()} Path" for p, _ in profile_list)
        lines.append(f"| Title | {wsums_header} | {path_header} |")
        lines.append("|" + "|".join(["---"] * (1 + len(profile_list) * 2)) + "|")
        for item_id in passing_all:
            first_profile = profile_list[0][0].name
            first_scored_item = item_score_map[item_id][first_profile]
            title = _resolve_title(item_id, first_scored_item.item.title, ai_title_maps)
            wsums = " | ".join(f"{item_score_map[item_id][p.name].weighted_sum:.2f}" for p, _ in profile_list)
            paths = " | ".join(item_score_map[item_id][p.name].inclusion_path or "—" for p, _ in profile_list)
            lines.append(f"| {title} | {wsums} | {paths} |")
        lines.append("")

    # Items passing some but not all profiles
    for p_focus, s_focus in profile_list:
        other_profiles = [(p, s) for p, s in profile_list if p.name != p_focus.name]
        exclusive = [
            item_id for item_id in all_ids_ordered
            if item_score_map.get(item_id, {}).get(p_focus.name) and item_score_map[item_id][p_focus.name].included
            and any(
                not (item_score_map.get(item_id, {}).get(p.name) and item_score_map[item_id][p.name].included)
                for p, _ in other_profiles
            )
        ]
        if exclusive:
            other_names = " and ".join(p.name for p, _ in other_profiles)
            lines.append(f"### Items passing {p_focus.name} but NOT {other_names} ({len(exclusive)})\n")
            excl_reason_headers = " | ".join(f"{p.name.capitalize()} exclusion" for p, _ in other_profiles)
            lines.append(f"| Title | {p_focus.name.capitalize()} WSum | Path | {excl_reason_headers} |")
            lines.append("|" + "|".join(["---"] * (3 + len(other_profiles))) + "|")
            for item_id in exclusive:
                focus_scored_item = item_score_map[item_id][p_focus.name]
                title = _resolve_title(item_id, focus_scored_item.item.title, ai_title_maps, p_focus.name)
                excl_reasons = []
                for p_other, _ in other_profiles:
                    other_scored_item = item_score_map.get(item_id, {}).get(p_other.name)
                    if other_scored_item and not other_scored_item.included:
                        failed = list(dict.fromkeys(g for gs in other_scored_item.failed_gates.values() for g in gs))
                        excl_reasons.append("Low " + ", ".join(failed) if failed else "excluded")
                    else:
                        excl_reasons.append("not scored")
                lines.append(
                    f"| {title} | {focus_scored_item.weighted_sum:.2f} | {focus_scored_item.inclusion_path} | "
                    + " | ".join(excl_reasons) + " |"
                )
            lines.append("")

    return lines


def _write_ranking_results(
    profiles_scored: dict,
    items_total: int,
    max_posts: int,
    ai_title_maps: dict[str, dict[str, str]] | None = None,
) -> None:
    """Regenerate ranking_results.md from the current run's scoring data."""
    _maps = ai_title_maps or {}
    lines = _build_header(items_total, profiles_scored)
    for profile, scored in profiles_scored.values():
        lines += _build_profile_section(profile, scored, max_posts, _maps)
    if len(profiles_scored) >= 2:
        lines += _build_cross_profile_section(profiles_scored, _maps)
    out = Path("artifacts/ranking_results.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def _write_run_log(scored_items: List[ScoredItem], profile_name: str) -> str:
    """Persist full scoring details to artifacts/blog-runs/YYYY-MM-DD-{profile}.json."""
    log_dir = Path("artifacts/blog-runs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{profile_name}.json"

    results = []
    for idx, scored_item in enumerate(scored_items, 1):
        results.append({
            "row": idx,
            "id": scored_item.item.id,
            "title": scored_item.item.title,
            "included": scored_item.included,
            "inclusion_path": scored_item.inclusion_path,
            "weighted_sum": scored_item.weighted_sum,
            "dimensions": scored_item.dimension_scores,
            "path_results": scored_item.path_results,
            "failed_gates": scored_item.failed_gates,
        })

    log_data = {
        "profile": profile_name,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "items_evaluated": len(scored_items),
        "items_included": sum(1 for scored_item in scored_items if scored_item.included),
        "items_excluded": sum(1 for scored_item in scored_items if not scored_item.included),
        "results": results,
    }
    log_path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"artifacts/blog-runs/{profile_name}.json"
