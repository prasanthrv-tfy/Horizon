"""horizon-upload-artifacts CLI: uploads the artifacts/ directory to a TrueFoundry ML repo.

Usage:
    uv run horizon-upload-artifacts --repo-name my-ml-repo           # upload files directly
    uv run horizon-upload-artifacts --repo-name my-ml-repo --zip     # upload as a zip archive

Requires TFY_API_KEY and TFY_HOST environment variables (or a .env file).
"""

import asyncio
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

ARTIFACTS_DIR = Path("artifacts")
LOGS_DIR = Path("artifacts/logs")


def _zip_artifacts(date_str: str) -> Path:
    zip_path = Path(f"{date_str}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(ARTIFACTS_DIR.rglob("*")):
            if file.is_file():
                zf.write(file, file.relative_to(ARTIFACTS_DIR.parent))
    return zip_path


async def _run(console: Console, ml_repo: str, as_zip: bool) -> None:
    try:
        from truefoundry.ml import ArtifactPath, get_client
    except ImportError:
        console.print("[red]✗ truefoundry is not installed. Run: uv sync --extra upload[/red]")
        sys.exit(1)

    date_str = datetime.now().strftime("%d-%b-%Y")

    if not ARTIFACTS_DIR.exists():
        console.print(f"[red]✗ Artifacts directory not found: {ARTIFACTS_DIR}[/red]")
        sys.exit(1)

    zip_path: Path | None = None
    try:
        if as_zip:
            with console.status(f"[cyan]Zipping {ARTIFACTS_DIR}/ → {date_str}.zip ...[/cyan]"):
                zip_path = _zip_artifacts(date_str)
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            console.print(f"[green]✓[/green] Zipped {size_mb:.1f} MB → {zip_path}")
            artifact_paths = [ArtifactPath(src=str(zip_path))]
        else:
            artifact_paths = [ArtifactPath(src=str(ARTIFACTS_DIR) + "/", dest="artifacts")]

        with console.status(f"[cyan]Uploading to ML repo '{ml_repo}' as '{date_str}' ...[/cyan]"):
            client = get_client()
            artifact_version = client.log_artifact(
                ml_repo=ml_repo,
                name=date_str,
                artifact_paths=artifact_paths,
            )
        console.print(f"[green]✓[/green] Uploaded: {artifact_version.fqn}")
    finally:
        if zip_path and zip_path.exists():
            zip_path.unlink()


def main() -> None:
    import argparse

    load_dotenv()

    parser = argparse.ArgumentParser(description="Upload artifacts/ to a TrueFoundry ML repo.")
    parser.add_argument("--repo-name", required=True, metavar="REPO", help="TrueFoundry ML repo name")
    parser.add_argument("--zip", action="store_true", help="Upload as a single zip archive instead of individual files")
    args = parser.parse_args()

    for var in ("TFY_API_KEY", "TFY_HOST"):
        if not os.environ.get(var):
            print(f"✗ {var} environment variable is not set.", file=sys.stderr)
            sys.exit(1)

    console = Console(record=True)
    console.print("[bold cyan]📦 Horizon Upload Artifacts — Starting...[/bold cyan]\n")
    try:
        asyncio.run(_run(console, args.repo_name, as_zip=args.zip))
    finally:
        (LOGS_DIR / "plain").mkdir(parents=True, exist_ok=True)
        (LOGS_DIR / "html").mkdir(parents=True, exist_ok=True)
        (LOGS_DIR / "plain" / "upload-artifacts.log").write_text(console.export_text(clear=False), encoding="utf-8")
        (LOGS_DIR / "html" / "upload-artifacts.html").write_text(console.export_html(), encoding="utf-8")
