#!/usr/bin/env python3
"""
PlaceBot GUI (Streamlit)
========================

A lightweight, point-and-click front-end for PlaceBot aimed at non-technical
users. It reuses the existing ``placebot.core`` modules and replaces the
interactive CLI prompts with widgets.

Run with:  ``placebot-gui``  (or ``streamlit run placebot/gui/app.py``)

Design notes
------------
* Streamlit reruns this script top-to-bottom on every interaction, so all
  wizard state lives in ``st.session_state``.
* We deliberately do NOT import ``placebot.cli.user_interface`` - its methods
  call ``input()``/``print()`` and would block or garble the GUI.
* Heavy work (processing) is gated behind an explicit button.
"""

import json
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import streamlit as st

from placebot.core.config import get_config
from placebot.core.data_dirs import (
    setup_directories,
    get_input_dir,
    get_output_dir,
    get_batch_jobs_dir,
)
from placebot.core.file_manager import DatasetManager, OutputManager
from placebot.core.dataset_preview import DatasetPreview
from placebot.core.model_selector import discover_models, load_model_profile
from placebot.core.model_comparison import ModelComparison
from placebot.core.cost_estimator import CostEstimator
from placebot.core.output_formatter import OutputFormatter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROVIDERS = [
    ("anthropic", "Anthropic (Claude)"),
    ("openai", "OpenAI (GPT)"),
    ("google", "Google (Gemini)"),
]

LOGO_PATH = Path(__file__).parent / "placebot_logo.png"


def get_logo_path():
    """Return the bundled PlaceBot logo path, or None if it is missing."""
    return str(LOGO_PATH) if LOGO_PATH.exists() else None


def open_in_file_manager(path: str) -> bool:
    """Open ``path`` in the operating system's file manager.

    The GUI runs locally (Streamlit serves the user's own machine), so we can
    reveal the output folder directly. Returns True on success.
    """
    try:
        if platform.system() == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def render_output_folder_link(label: str = "Output folder"):
    """Render the output folder path with a button to open it locally."""
    out_dir = str(get_output_dir())
    col1, col2 = st.columns([3, 1])
    col1.caption(f"{label}: `{out_dir}`")
    if col2.button("Open folder", key=f"open_{label}"):
        if open_in_file_manager(out_dir):
            st.toast("Opened output folder in your file browser.")
        else:
            st.warning(
                "Could not open the folder automatically. Copy the path above "
                "into your file browser."
            )


def _model_needs_key(model_config: dict) -> bool:
    """Local (Ollama/Qwen) models do not require an API key."""
    name = (model_config.get("name", "") + model_config.get("provider", "")).lower()
    return not ("qwen" in name or "ollama" in name or "local" in name)


def _model_has_key(model_config: dict) -> bool:
    """Whether the model is ready to run (local, or has a key configured)."""
    if not _model_needs_key(model_config):
        return True
    key = model_config.get("api_key") or ""
    return len(key) > 10


# These delegate to OutputFormatter so the GUI's downloads/auto-saves are
# byte-for-byte identical to the CLI's files: same canonical column order, and
# a UTF-8 BOM on CSV so Excel renders accents (e.g. "Rhône") correctly.
def records_to_csv_bytes(records: list) -> bytes:
    return OutputFormatter.records_to_csv_bytes(records)


def records_to_json_bytes(records: list) -> bytes:
    return OutputFormatter.records_to_json_bytes(records)


def records_to_geojson_bytes(records: list) -> bytes:
    return OutputFormatter.records_to_geojson_bytes(records)


_DOWNLOAD_BUILDERS = {
    "csv": ("text/csv", "csv", records_to_csv_bytes),
    "json": ("application/json", "json", records_to_json_bytes),
    "geojson": ("application/geo+json", "geojson", records_to_geojson_bytes),
}


def _render_download_buttons(records, formats, stem, key_prefix, heading="Download"):
    """Render optional 'download a copy' buttons for the given formats."""
    formats = [f for f in formats if f in _DOWNLOAD_BUILDERS] or ["csv"]
    st.subheader(heading)
    cols = st.columns(len(formats))
    for col, fmt in zip(cols, formats):
        mime, ext, builder = _DOWNLOAD_BUILDERS[fmt]
        col.download_button(
            f"Download {fmt.upper()}",
            data=builder(records),
            file_name=f"{stem}.{ext}",
            mime=mime,
            key=f"{key_prefix}_{fmt}",
        )


def _load_all_model_configs(model_names: tuple) -> list:
    """Load model profiles. Not cached: configs hold live function/module refs."""
    configs = []
    for name in model_names:
        cfg = load_model_profile(name)
        if cfg:
            cfg["_file"] = name
            configs.append(cfg)
    return configs


# ---------------------------------------------------------------------------
# Sidebar: API keys (always available)
# ---------------------------------------------------------------------------


def _render_single_key(config, provider, label, configured):
    """Single API-key editor (Anthropic / OpenAI)."""
    value = st.text_input(
        f"{label} key",
        type="password",
        key=f"key_input_{provider}",
        placeholder="Paste your API key here",
        label_visibility="collapsed",
    )
    col1, col2 = st.columns(2)
    if col1.button("Save", key=f"save_{provider}"):
        if value:
            config.save_api_key(provider, value)
            st.success("Saved!")
            st.rerun()
        else:
            st.warning("Enter a key first.")
    if configured and col2.button("Clear", key=f"clear_{provider}"):
        config.save_api_key(provider, "")
        st.rerun()


def _render_google_keys(config):
    """Google/Gemini editor supporting multiple keys for large jobs.

    The primary key is used by every Gemini job; additional keys mirror the
    ``GOOGLE_API_KEY_2`` ... convention and let you spread very large batch
    jobs across separate quotas.
    """
    existing = config.get_google_api_keys()
    max_keys = config.MAX_GOOGLE_KEYS

    new_values = []
    prev_value = None  # value of the previously rendered slot
    for slot in range(max_keys):
        current = existing[slot] if slot < len(existing) else ""
        # Show the next optional slot only once the preceding one is filled,
        # to keep the panel tidy for users who only need a single key. Stop as
        # soon as we hit an empty trailing slot.
        if slot > 0 and not current and not prev_value:
            break
        if slot == 0:
            field_label = "Primary key (GOOGLE_API_KEY)"
        else:
            field_label = (
                f"Additional key {slot + 1} (GOOGLE_API_KEY_{slot + 1}) — optional"
            )
        value = st.text_input(
            field_label,
            value=current,
            type="password",
            key=f"google_key_{slot}",
            placeholder="Paste your Gemini API key here",
        )
        new_values.append(value)
        prev_value = value

    st.caption(
        "Add more than one key only if you process very large datasets and "
        "want to spread the load across separate Gemini quotas."
    )
    col1, col2 = st.columns(2)
    if col1.button("Save", key="save_google"):
        config.save_google_api_keys(new_values)
        st.success("Saved!")
        st.rerun()
    if existing and col2.button("Clear all", key="clear_google"):
        config.save_google_api_keys([])
        st.rerun()


def render_sidebar():
    config = get_config()

    logo = get_logo_path()
    if logo:
        st.sidebar.image(logo, use_container_width=True)

    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Process data", "Batch downloads"],
        label_visibility="collapsed",
        key="page",
    )

    st.sidebar.divider()
    st.sidebar.header("API Keys")
    st.sidebar.caption(
        "Keys are saved to `~/.placebot/.env` on your computer and remembered "
        "between sessions. Local (Qwen/Ollama) models need no key."
    )

    status = config.check_api_keys()
    for provider, label in PROVIDERS:
        configured = status.get(provider, False)
        badge = "Configured" if configured else "Not set"
        with st.sidebar.expander(f"{label} — {badge}", expanded=not configured):
            if provider == "google":
                _render_google_keys(config)
            else:
                _render_single_key(config, provider, label, configured)

    st.sidebar.divider()
    with st.sidebar:
        render_output_folder_link("Data folder")
    if st.sidebar.button("Start over"):
        for k in [
            "step",
            "selected_dataset",
            "dataset_records",
            "mode",
            "model_file",
            "formats",
            "batch_size",
            "run_results",
        ]:
            st.session_state.pop(k, None)
        st.rerun()

    return page


# ---------------------------------------------------------------------------
# Step 1: choose / upload a dataset
# ---------------------------------------------------------------------------


def step_dataset(dataset_manager: DatasetManager):
    st.header("1 · Choose your data")
    st.write(
        "Upload a spreadsheet of localities (CSV or TSV), or pick one already "
        "in your input folder. It needs an **ID** column and a **locality "
        "description** column."
    )

    uploaded = st.file_uploader("Upload a CSV or TSV file", type=["csv", "tsv", "txt"])
    if uploaded is not None:
        dest = os.path.join(str(get_input_dir()), uploaded.name)
        with open(dest, "wb") as f:
            f.write(uploaded.getbuffer())
        st.success(f"Uploaded **{uploaded.name}**")

    datasets = dataset_manager.discover_datasets()
    # Skip the helper README.txt that PlaceBot drops in the input folder
    datasets = [d for d in datasets if d["filename"].lower() != "readme.txt"]
    if not datasets:
        st.info("No datasets found yet. Upload a file above to get started.")
        return

    labels = [
        f"{d['filename']}  —  {d['row_count']:,} records, {len(d['columns'])} columns"
        for d in datasets
    ]
    # Default to the most recently uploaded file if present
    default_idx = 0
    if uploaded is not None:
        for i, d in enumerate(datasets):
            if d["filename"] == uploaded.name:
                default_idx = i
                break

    choice = st.selectbox(
        "Select a dataset",
        range(len(datasets)),
        format_func=lambda i: labels[i],
        index=default_idx,
    )
    selected = datasets[choice]

    # Preview
    records = dataset_manager.load_dataset(selected)
    stats = DatasetPreview.get_statistics(records)

    c1, c2, c3 = st.columns(3)
    c1.metric("Records", f"{stats['total_records']:,}")
    c2.metric("Columns", stats.get("field_count", 0))
    c3.metric("Has locality text", "Yes" if stats.get("has_locality") else "No")

    st.caption("Preview (first rows):")
    try:
        import pandas as pd

        st.dataframe(pd.DataFrame(records[:10]), use_container_width=True)
    except Exception:
        st.write(records[:10])

    if not stats.get("has_locality"):
        st.warning(
            "No obvious locality column detected. PlaceBot looks for a column "
            "containing 'locality' or 'location'. It may still work, but "
            "double-check your file."
        )

    if st.button("Continue →", type="primary"):
        st.session_state.selected_dataset = selected
        st.session_state.dataset_records = records
        st.session_state.step = "configure"
        st.rerun()


# ---------------------------------------------------------------------------
# Step 2: configure (mode, model, formats) + cost estimate
# ---------------------------------------------------------------------------


def step_configure():
    selected = st.session_state.selected_dataset
    num_records = selected["row_count"]

    st.header("2 · Choose how to process")
    st.caption(f"Dataset: **{selected['filename']}** · {num_records:,} records")

    # --- Mode ---
    mode_label = st.radio(
        "Processing mode",
        ["Real-time (results now)", "Batch (cheaper, up to 24h)"],
        help="Real-time is best for small datasets (under ~1,000 records). "
        "Batch is ~50% cheaper for large jobs. For very large jobs "
        "(3,000+) use the command line's staggered mode.",
    )
    mode = "realtime" if mode_label.startswith("Real-time") else "batch"

    # --- Model selection with comparison table ---
    model_names = tuple(discover_models())
    if not model_names:
        st.error("No model profiles found.")
        return
    configs = _load_all_model_configs(model_names)

    comparisons = ModelComparison.compare_models(configs, num_records, mode)
    comp_by_name = {c["model_name"]: c for c in comparisons}

    import pandas as pd

    st.subheader("Available models")
    st.caption(
        "Tick **Use** to choose the model to run. Models marked *Needs API "
        "key* must be set up in the sidebar first."
    )

    file_by_index = [cfg["_file"] for cfg in configs]
    ready_files = [c["_file"] for c in configs if _model_has_key(c)]
    if not ready_files:
        st.warning(
            "No models are ready. Add an API key in the sidebar, or "
            "install a local Qwen model."
        )
        return

    # Persist the chosen model across reruns; default to the first ready model.
    prev = st.session_state.get("model_file")
    if prev not in file_by_index:
        prev = ready_files[0]

    rows = []
    for cfg in configs:
        comp = comp_by_name.get(cfg.get("name", ""), {})
        ready = _model_has_key(cfg)
        rows.append(
            {
                "Use": cfg["_file"] == prev,
                "Model": cfg.get("name", cfg.get("_file")),
                "Vendor": comp.get("vendor", cfg.get("provider", "")),
                "Est. cost": (
                    "Free"
                    if comp.get("is_local")
                    else f"${comp.get('estimated_cost', 0):.4f}"
                ),
                "Est. time (min)": comp.get("estimated_time_minutes", "—"),
                "Ready": "Yes" if ready else "Needs API key",
            }
        )

    edited = st.data_editor(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        disabled=["Model", "Vendor", "Est. cost", "Est. time (min)", "Ready"],
        column_config={
            "Use": st.column_config.CheckboxColumn(
                "Use",
                help="Select this single model to run",
                default=False,
            ),
        },
        # Re-key on the current selection so the editor's accumulated edit
        # state resets whenever the chosen model changes. Without this, old
        # ticks linger and the single-select logic can flip back unexpectedly.
        key=f"model_table_{prev}",
    )

    # The checkbox column behaves like a radio: resolve a single selection,
    # preferring any newly-ticked row over the previous choice.
    checked = [i for i in edited.index if bool(edited.loc[i, "Use"])]
    selected_file = prev
    if checked:
        newly = [file_by_index[i] for i in checked if file_by_index[i] != prev]
        selected_file = newly[0] if newly else file_by_index[checked[0]]
    st.session_state.model_file = selected_file

    model_file = selected_file
    model_config = next(c for c in configs if c["_file"] == model_file)

    if not _model_has_key(model_config):
        st.warning(
            f"**{model_config.get('name', model_file)}** needs an API key. "
            "Add one in the sidebar, then it will be ready to run."
        )
        return

    # --- Cost estimate ---
    cost = CostEstimator.estimate_cost(
        num_records,
        model_config,
        processing_mode=mode,
        with_caching="cached" in model_config.get("name", "").lower(),
    )
    st.subheader("Estimated cost")
    c1, c2, c3 = st.columns(3)
    c1.metric("Records", f"{cost['num_records']:,}")
    c2.metric("Estimated cost", f"${cost['estimated_cost']:.4f}")
    c3.metric("Savings", f"{cost['savings_percentage']:.0f}%")
    st.caption(
        "Costs are estimates based on typical prompt sizes. Local models are free."
    )

    # --- Output formats ---
    st.subheader("Output formats")
    formats = st.multiselect(
        "Download results as",
        ["csv", "json", "geojson"],
        default=["csv"],
        format_func=lambda f: {
            "csv": "CSV (spreadsheet)",
            "json": "JSON",
            "geojson": "GeoJSON (maps/GIS)",
        }[f],
    )

    # --- Real-time batch size ---
    batch_size = 8
    if mode == "realtime":
        batch_size = st.number_input(
            "Records per batch",
            min_value=1,
            max_value=50,
            value=8,
            help="How many records to send per group. Smaller = more reliable.",
        )

    col1, col2 = st.columns([1, 1])
    if col1.button("← Back"):
        st.session_state.step = "dataset"
        st.rerun()
    if col2.button("Start processing →", type="primary"):
        st.session_state.mode = mode
        st.session_state.model_file = model_file
        st.session_state.formats = formats or ["csv"]
        st.session_state.batch_size = int(batch_size)
        st.session_state.step = "run"
        st.session_state.pop("run_results", None)
        st.rerun()


# ---------------------------------------------------------------------------
# Step 3: run + results
# ---------------------------------------------------------------------------


def step_run(dataset_manager: DatasetManager):
    selected = st.session_state.selected_dataset
    mode = st.session_state.mode
    model_config = load_model_profile(st.session_state.model_file)

    st.header("3 · Processing")

    if "run_results" not in st.session_state:
        if mode == "realtime":
            _run_realtime(dataset_manager, selected, model_config)
        else:
            _run_batch(selected, model_config)

    _show_results()


def _run_realtime(dataset_manager, selected, model_config):
    from placebot.core.batch_processor import BatchProcessor

    total = selected["row_count"]
    bar = st.progress(0.0)
    status = st.empty()

    def cb(info):
        done, tot = info.get("processed", 0), info.get("total", total) or total
        bar.progress(min(done / tot, 1.0) if tot else 0.0)
        status.write(f"Processed {done:,} / {tot:,}")

    processor = BatchProcessor(dataset_manager, OutputManager)
    with st.spinner("Contacting the AI model and processing records…"):
        try:
            results = processor.process_dataset(
                selected,
                model_config,
                batch_size=st.session_state.batch_size,
                save_progress=True,
                progress_callback=cb,
            )
        except Exception as e:
            st.error(f"Processing failed: {e}")
            return

    bar.progress(1.0)

    # Auto-save the chosen formats into the output folder (next to the .tsv),
    # so users get CSV/JSON/GeoJSON without a manual browser download.
    saved_files = {}
    if results.get("success"):
        records = results.get("processed_records", [])
        tsv_path = results.get("output_path", "")
        formats = st.session_state.get("formats", ["csv"])
        if records and tsv_path:
            base_path = os.path.splitext(tsv_path)[0]
            saved_files = OutputFormatter.write_output(records, base_path, formats)

    st.session_state.run_results = {
        "type": "realtime",
        "results": results,
        "saved_files": saved_files,
    }


def _run_batch(selected, model_config):
    from placebot.core.async_batch_processor import (
        AnthropicBatchProcessor,
        OpenAIBatchProcessor,
        GeminiBatchProcessor,
    )
    from placebot.core.ai_processor import AIProcessor

    provider = (model_config.get("provider", "") or "").lower()
    api_key = model_config.get("api_key", "")
    model_id = model_config.get("model_id", "")

    if "anthropic" in provider:
        bp = AnthropicBatchProcessor(api_key, model_id)
    elif "openai" in provider or "gpt" in provider:
        bp = OpenAIBatchProcessor(api_key, model_id)
    elif "google" in provider or "gemini" in provider:
        bp = GeminiBatchProcessor(api_key, model_id)
    else:
        st.error(
            f"Batch mode is not supported for provider '{provider}'. "
            "Use Real-time mode instead."
        )
        return

    records = st.session_state.dataset_records
    prompt_template = AIProcessor(model_config)._get_full_instructions()

    batch_dir = os.path.join(str(get_output_dir()), "batch_jobs")
    os.makedirs(batch_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = os.path.splitext(selected["filename"])[0]
    model_safe = model_config.get("name", "model").replace(" ", "_")
    batch_name = f"{stem}_{model_safe}_{timestamp}"

    with st.spinner("Submitting batch job…"):
        try:
            if "openai" in provider or "gpt" in provider:
                batch_file = os.path.join(batch_dir, f"{batch_name}.jsonl")
                bp.prepare_batch_file(records, prompt_template, batch_file)
                batch_id = bp.submit_batch(batch_file, batch_name)
            else:
                requests_list = bp.prepare_batch_requests(records, prompt_template)
                batch_id = bp.submit_batch(requests_list, batch_name)
        except Exception as e:
            st.error(f"Batch submission failed: {e}")
            return

    info = {
        "batch_id": batch_id,
        "batch_name": batch_name,
        "provider": provider,
        "model": model_id,
        "dataset": selected["filename"],
        "record_count": len(records),
        "submitted_at": timestamp,
        "output_formats": st.session_state.formats,
    }
    info_file = os.path.join(batch_dir, f"{batch_name}_info.json")
    with open(info_file, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

    st.session_state.run_results = {
        "type": "batch",
        "batch_id": batch_id,
        "info_file": info_file,
    }


def _show_results():
    res = st.session_state.get("run_results")
    if not res:
        return

    if res["type"] == "batch":
        st.success("Batch submitted!")
        st.write(f"**Batch ID:** `{res['batch_id']}`")
        st.write(
            "Your results will be ready within 24 hours (usually much "
            "faster). When it's done, open **Batch downloads** in the sidebar "
            "to fetch your results — no command line needed."
        )
        st.caption(f"Job details saved to: {res['info_file']}")
        return

    results = res["results"]
    if not results.get("success"):
        st.error(
            f"Processing did not complete: {results.get('error', 'unknown error')}"
        )
        return

    records = results.get("processed_records", [])
    st.success(f"Done! Processed {len(records):,} records.")

    # Files were saved automatically to the output folder.
    saved_files = res.get("saved_files", {})
    st.write("**Saved to your output folder:**")
    st.write(f"- `{os.path.basename(results.get('output_path', ''))}` (TSV)")
    for fmt, path in saved_files.items():
        st.write(f"- `{os.path.basename(path)}` ({fmt.upper()})")
    render_output_folder_link("Output folder")

    with st.expander("Summary report"):
        st.text(results.get("summary_report", ""))

    try:
        import pandas as pd

        st.dataframe(pd.DataFrame(records), use_container_width=True)
    except Exception:
        st.write(records[:50])

    _render_download_buttons(
        records,
        st.session_state.get("formats", ["csv"]),
        stem=os.path.splitext(st.session_state.selected_dataset["filename"])[0]
        + "_placebot",
        key_prefix="dl",
        heading="Or download a copy",
    )


# ---------------------------------------------------------------------------
# Batch downloads page
# ---------------------------------------------------------------------------


def _list_batch_jobs():
    """Return submitted batch jobs (newest first) from the batch_jobs folder."""
    batch_dir = str(get_batch_jobs_dir())
    jobs = []
    if os.path.isdir(batch_dir):
        for fname in os.listdir(batch_dir):
            if not fname.endswith("_info.json"):
                continue
            path = os.path.join(batch_dir, fname)
            try:
                if os.path.getsize(path) == 0:
                    continue
                with open(path, encoding="utf-8") as f:
                    info = json.load(f)
                if "batch_id" in info:
                    jobs.append(info)
            except (json.JSONDecodeError, OSError):
                continue
    jobs.sort(key=lambda i: i.get("submitted_at", ""), reverse=True)
    return jobs


def step_batch_downloads():
    from placebot.cli.batch_download import fetch_batch_results

    st.header("Batch downloads")
    st.write(
        "Submitted a batch job? Once it finishes (usually within 24 hours) "
        "fetch and download the results here — no command line required."
    )

    jobs = _list_batch_jobs()
    if not jobs:
        st.info(
            "No batch jobs found yet. Submit one from **Process data** using "
            "the *Batch* processing mode."
        )
        return

    labels = [
        f"{j.get('batch_name', j['batch_id'])} — "
        f"{j.get('record_count', '?')} records, submitted {j.get('submitted_at', '?')}"
        for j in jobs
    ]
    idx = st.selectbox(
        "Select a batch job",
        range(len(jobs)),
        format_func=lambda i: labels[i],
    )
    job = jobs[idx]

    c1, c2, c3 = st.columns(3)
    c1.metric("Provider", job.get("provider", "—"))
    c2.metric("Records", f"{job.get('record_count', 0):,}")
    c3.metric("Model", job.get("model", "—"))
    st.caption(f"Batch ID: `{job['batch_id']}`")

    if st.button("Download results", type="primary"):
        with st.spinner("Fetching results from the provider…"):
            result = fetch_batch_results(job["batch_id"])
        st.session_state.batch_dl_result = result

    result = st.session_state.get("batch_dl_result")
    if not result:
        return
    # Only show results for the currently-selected job
    if result.get("info", {}).get("batch_id") != job["batch_id"]:
        return

    if not result["success"]:
        st.warning(result["error"])
        return

    records = result["records"]
    formats = job.get("output_formats") or ["csv"]
    stem = job.get("batch_name", "placebot")

    # Auto-save the chosen formats into the output folder, matching real-time
    # mode (same canonical columns and UTF-8 BOM on CSV). Done once per fetch.
    saved_files = result.get("saved_files")
    if saved_files is None:
        base_path = os.path.join(str(get_output_dir()), stem)
        saved_files = OutputFormatter.write_output(records, base_path, formats)
        result["saved_files"] = saved_files  # cache on the stored result

    st.success(f"Downloaded {len(records):,} records.")
    st.write("**Saved to your output folder:**")
    for fmt, path in saved_files.items():
        st.write(f"- `{os.path.basename(path)}` ({fmt.upper()})")
    render_output_folder_link("Output folder")

    try:
        import pandas as pd

        st.dataframe(pd.DataFrame(records), use_container_width=True)
    except Exception:
        st.write(records[:50])

    _render_download_buttons(
        records,
        formats,
        stem=stem,
        key_prefix="batch_dl",
        heading="Or download a copy",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    logo = get_logo_path()
    st.set_page_config(
        page_title="PlaceBot",
        page_icon=logo or "🌍",
        layout="wide",
    )
    setup_directories()

    header_cols = st.columns([1, 6])
    if logo:
        header_cols[0].image(logo, width=90)
    with header_cols[1]:
        st.title("PlaceBot")
        st.caption("Turn locality descriptions into geographic coordinates.")

    page = render_sidebar()

    if page == "Batch downloads":
        step_batch_downloads()
        return

    step = st.session_state.get("step", "dataset")
    dataset_manager = DatasetManager(
        input_folder=str(get_input_dir()),
        output_folder=str(get_output_dir()),
    )

    if step == "dataset":
        step_dataset(dataset_manager)
    elif step == "configure":
        step_configure()
    elif step == "run":
        step_run(dataset_manager)


# Streamlit executes this script with __name__ == "__main__".
if __name__ == "__main__":
    main()
