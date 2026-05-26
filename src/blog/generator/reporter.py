import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .loader import _clean_title
from src.blog.models import BlogPost, ScoredItem
from src.blog.profiles.profile import BlogPromptProfile


def _write_ranking_results(
    profiles_scored: dict,
    items_total: int,
    max_posts: int,
) -> None:
    """Regenerate ranking_results.md from the current run's scoring data."""
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
            title = _clean_title(si.item.title).replace("|", "\\|")
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
                    lines.append(f"| {rank} | {_clean_title(si.item.title)} | {si.inclusion_path} | {si.weighted_sum:.2f} |")
            else:
                lines.append("| Rank | Title | WSum |")
                lines.append("|---|---|---|")
                for rank, si in enumerate(top_included, 1):
                    lines.append(f"| {rank} | {_clean_title(si.item.title)} | {si.weighted_sum:.2f} |")
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
                lambda top: f"{_clean_title(top.item.title)} ({top.weighted_sum:.2f})" if top else "—"
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
                title = _clean_title(id_to_si[iid][profile_list[0][0].name].item.title)
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
                    title = _clean_title(si_f.item.title)
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


def _write_run_log(scored_items: List[ScoredItem], profile_name: str) -> str:
    """Persist full scoring details to artifacts/blog-runs/YYYY-MM-DD-{profile}.json."""
    log_dir = Path("artifacts/blog-runs")
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
        "run_at": datetime.now(timezone.utc).isoformat(),
        "items_evaluated": len(scored_items),
        "items_included": sum(1 for si in scored_items if si.included),
        "items_excluded": sum(1 for si in scored_items if not si.included),
        "results": results,
    }
    log_path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False), encoding="utf-8")
    console_path = f"artifacts/blog-runs/{today}-{profile_name}.json"
    return console_path
