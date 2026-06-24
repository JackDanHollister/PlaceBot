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
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import dotenv_values

from placebot.core.config import get_config, get_user_env_path
from placebot.core.data_dirs import (
    setup_directories,
    get_input_dir,
    get_output_dir,
    get_batch_jobs_dir,
)
from placebot.core.file_manager import DatasetManager, OutputManager
from placebot.core.dataset_preview import DatasetPreview
from placebot.core.model_selector import (
    clear_ollama_cache,
    get_ollama_models_cached,
    is_local_model_config,
    load_all_model_profiles,
    load_model_profile,
)
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
    ("openrouter", "OpenRouter"),
]

LOGO_PATH = Path(__file__).parent / "placebot_logo.png"
PROVIDER_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


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


def _safe_uploaded_filename(filename: str) -> str:
    """Return a basename-only, conservative upload filename."""
    base = os.path.basename(filename or "").strip()
    base = re.sub(r"[^A-Za-z0-9._ -]+", "_", base)
    base = base.lstrip(".")
    return base or "uploaded_file"


def _session_keys() -> dict:
    """Session-only API keys currently active in this GUI process."""
    return st.session_state.setdefault("session_api_keys", {})


def _google_env_vars(max_keys: Optional[int] = None) -> tuple:
    max_keys = max_keys or get_config().MAX_GOOGLE_KEYS
    return tuple(
        "GOOGLE_API_KEY" if slot == 1 else f"GOOGLE_API_KEY_{slot}"
        for slot in range(1, max_keys + 1)
    )


def _saved_env_values() -> dict:
    """Values explicitly remembered in the GUI's user-level .env file."""
    env_path = get_user_env_path()
    if not env_path.exists():
        return {}
    return {key: value for key, value in dotenv_values(env_path).items() if value}


def _saved_env_value(env_var: str) -> Optional[str]:
    value = _saved_env_values().get(env_var)
    return str(value) if value else None


def _set_session_api_key(provider: str, value: str) -> None:
    """Make a pasted API key available for this GUI session only."""
    env_var = PROVIDER_ENV_VARS[provider]
    os.environ[env_var] = value
    _session_keys()[env_var] = value


def _clear_session_api_key(provider: str) -> None:
    env_var = PROVIDER_ENV_VARS[provider]
    _session_keys().pop(env_var, None)
    saved = _saved_env_value(env_var)
    if saved:
        os.environ[env_var] = saved
    else:
        os.environ.pop(env_var, None)


def _set_session_google_api_keys(values: list) -> None:
    """Set one or more Google keys for this GUI session only."""
    for env_var in _google_env_vars():
        _session_keys().pop(env_var, None)
        os.environ.pop(env_var, None)
    for slot, value in enumerate(values, start=1):
        env_var = "GOOGLE_API_KEY" if slot == 1 else f"GOOGLE_API_KEY_{slot}"
        os.environ[env_var] = value
        _session_keys()[env_var] = value


def _clear_session_google_api_keys() -> None:
    for env_var in _google_env_vars():
        _session_keys().pop(env_var, None)
        saved = _saved_env_value(env_var)
        if saved:
            os.environ[env_var] = saved
        else:
            os.environ.pop(env_var, None)


def _provider_available(config, provider: str) -> bool:
    if provider == "google":
        return bool(config.get_google_api_keys())
    return bool(config.get_api_key(provider))


def _provider_saved_configured(provider: str) -> bool:
    if provider == "google":
        return any(env in _saved_env_values() for env in _google_env_vars())
    return bool(_saved_env_value(PROVIDER_ENV_VARS[provider]))


def _provider_session_configured(provider: str) -> bool:
    if provider == "google":
        return any(env in _session_keys() for env in _google_env_vars())
    return PROVIDER_ENV_VARS[provider] in _session_keys()


def _model_needs_key(model_config: dict) -> bool:
    """Local (Ollama/Qwen) models do not require an API key."""
    return not is_local_model_config(model_config)


def _model_has_key(model_config: dict) -> bool:
    """Whether the model is ready to run (local, or has a key configured)."""
    if is_local_model_config(model_config):
        return bool(model_config.get("local_ready"))
    key = model_config.get("api_key") or ""
    return len(key) > 10


def _model_ready_label(model_config: dict) -> str:
    """Short GUI status for model readiness."""
    if _model_has_key(model_config):
        return "Yes"
    if is_local_model_config(model_config):
        return model_config.get("local_status", "Local model unavailable")
    return "Needs API key"


def _model_select_label(model_config: dict) -> str:
    """Readable label for selectbox-style model pickers."""
    name = model_config.get("name", model_config.get("_file", "Unknown model"))
    model_id = model_config.get("model_id", "")
    ready = _model_ready_label(model_config)
    if model_id:
        return f"{name} — {model_id} — {ready}"
    return f"{name} — {ready}"


def _ollama_model_sidebar_label(model_info: dict) -> str:
    """Readable installed-model label for the local setup sidebar."""
    name = model_info.get("name", "Unknown model")
    details = model_info.get("details") or {}
    metadata = ", ".join(
        item
        for item in (
            details.get("parameter_size"),
            details.get("family"),
            details.get("quantization_level"),
        )
        if item
    )
    return f"`{name}` ({metadata})" if metadata else f"`{name}`"


def _how_to_use_steps() -> list:
    """Step-by-step GUI instructions shown from the header help button."""
    return [
        (
            "Add model access",
            "For cloud models, paste an API key in the sidebar. For local "
            "models, start Ollama and check **Local models (Ollama)** in the "
            "sidebar.",
        ),
        (
            "Choose your data",
            "Upload a CSV/TSV file or select one already in the input folder. "
            "The file needs an ID/barcode column and a locality/location text "
            "column.",
        ),
        (
            "Pick processing settings",
            "Scroll down to section 2, choose real-time or batch processing, "
            "then select a cloud/API model or **Local Ollama**.",
        ),
        (
            "Review cost and outputs",
            "Check the estimate, choose CSV/JSON/GeoJSON outputs, and adjust "
            "the batch size for real-time runs if needed.",
        ),
        (
            "Run and collect results",
            "Click **Start processing** — section 3 appears below with live "
            "progress. Results are saved automatically in the output folder "
            "and can also be downloaded from that section.",
        ),
        (
            "Use batch downloads later",
            "For batch or staggered jobs, return to **Batch downloads** in the "
            "sidebar to fetch completed provider results.",
        ),
    ]


def _render_how_to_use_panel() -> None:
    """Render the collapsible top-of-page user guide."""
    st.subheader("How to use PlaceBot")
    for index, (heading, detail) in enumerate(_how_to_use_steps(), start=1):
        st.markdown(f"**{index}. {heading}**  \n{detail}")


def _record_failed(record: dict) -> bool:
    """Infer whether a processed output row represents a failed AI call."""
    notes = str(record.get("Processing_Notes", "")).lower()
    source = str(record.get("Coordinate_Source", "")).lower()
    return (
        "processing failed" in notes
        or "response parsing failed" in notes
        or "| error:" in notes
        or source == "failed"
    )


def _processing_counts(records: list) -> dict:
    """Count successful and failed processed rows."""
    failed = sum(1 for record in records if _record_failed(record))
    total = len(records)
    return {"total": total, "failed": failed, "successful": total - failed}


# These delegate to OutputFormatter so the GUI's downloads/auto-saves are
# byte-for-byte identical to the CLI's files: same canonical column order, and
# a UTF-8 BOM on CSV so Excel renders accents (e.g. "Rhône") correctly.
def records_to_csv_bytes(records: list, dwc: bool = False, column_order: list = None) -> bytes:
    return OutputFormatter.records_to_csv_bytes(records, dwc=dwc, column_order=column_order)


def records_to_tsv_bytes(records: list, dwc: bool = False, column_order: list = None) -> bytes:
    return OutputFormatter.records_to_tsv_bytes(records, dwc=dwc, column_order=column_order)


def records_to_json_bytes(records: list, dwc: bool = False, column_order: list = None) -> bytes:
    # JSON preserves dict insertion order, so column_order is accepted but unused.
    return OutputFormatter.records_to_json_bytes(records, dwc=dwc)


def records_to_geojson_bytes(records: list, dwc: bool = False, column_order: list = None) -> bytes:
    # GeoJSON property order follows dict insertion order; column_order unused.
    return OutputFormatter.records_to_geojson_bytes(records, dwc=dwc)


_DOWNLOAD_BUILDERS = {
    "csv": ("text/csv", "csv", records_to_csv_bytes),
    "tsv": ("text/tab-separated-values", "tsv", records_to_tsv_bytes),
    "json": ("application/json", "json", records_to_json_bytes),
    "geojson": ("application/geo+json", "geojson", records_to_geojson_bytes),
}


def _render_download_buttons(records, formats, stem, key_prefix, heading="Download",
                             dwc=False, column_order=None):
    """Render optional 'download a copy' buttons for the given formats."""
    formats = [f for f in formats if f in _DOWNLOAD_BUILDERS] or ["csv"]
    st.subheader(heading)
    cols = st.columns(len(formats))
    for col, fmt in zip(cols, formats):
        mime, ext, builder = _DOWNLOAD_BUILDERS[fmt]
        col.download_button(
            f"Download {fmt.upper()}",
            data=builder(records, dwc=dwc, column_order=column_order),
            file_name=f"{stem}.{ext}",
            mime=mime,
            key=f"{key_prefix}_{fmt}",
        )


def _load_all_model_configs(model_names: tuple) -> list:
    """Load model profiles.

    Cheap to call repeatedly: model_selector caches the imported profile
    modules (by path + mtime) and the Ollama probe (15s TTL) at module level,
    while key availability is recomputed fresh on every call.
    """
    if model_names:
        configs = []
        for name in model_names:
            cfg = load_model_profile(name)
            if cfg:
                cfg["_file"] = name
                configs.append(cfg)
        return configs
    return load_all_model_profiles(include_dynamic_ollama=True)


def _dataset_records_cached(dataset_manager, selected: dict) -> list:
    """Load a dataset's records, reusing the previous load when unchanged.

    The single-page layout re-renders the data section on every rerun, so
    re-reading a large CSV each time would undo the responsiveness gains from
    model caching. Keyed by (filename, row_count) in session state.
    """
    cache_key = (selected["filename"], selected["row_count"])
    cached = st.session_state.get("_dataset_cache")
    if cached is not None and cached[0] == cache_key:
        return cached[1]
    records = dataset_manager.load_dataset(selected)
    st.session_state["_dataset_cache"] = (cache_key, records)
    return records


# ---------------------------------------------------------------------------
# Sidebar: API keys (always available)
# ---------------------------------------------------------------------------


def _render_single_key(config, provider, label, saved):
    """Single API-key editor (Anthropic / OpenAI / OpenRouter)."""
    value = st.text_input(
        f"{label} key",
        type="password",
        key=f"key_input_{provider}",
        placeholder="Paste your API key here",
        label_visibility="collapsed",
    )
    remember = st.checkbox("Remember on this computer", key=f"remember_{provider}")
    col1, col2, col3 = st.columns(3)
    if col1.button("Use key", key=f"use_{provider}"):
        if value:
            if remember:
                config.save_api_key(provider, value)
                _session_keys().pop(PROVIDER_ENV_VARS[provider], None)
                st.success("Saved for future sessions.")
            else:
                _set_session_api_key(provider, value)
                st.success("Using key for this session.")
            st.rerun()
        else:
            st.warning("Enter a key first.")
    if _provider_session_configured(provider) and col2.button(
        "Forget session", key=f"clear_session_{provider}"
    ):
        _clear_session_api_key(provider)
        st.rerun()
    if saved and col3.button("Clear saved", key=f"clear_{provider}"):
        config.save_api_key(provider, "")
        env_var = PROVIDER_ENV_VARS[provider]
        if env_var in _session_keys():
            os.environ[env_var] = _session_keys()[env_var]
        st.rerun()


def _render_google_keys(config):
    """Google/Gemini editor supporting multiple keys for large jobs.

    The primary key is used by every Gemini job; additional keys mirror the
    ``GOOGLE_API_KEY_2`` ... convention and let you spread very large batch
    jobs across separate quotas.
    """
    saved = _provider_saved_configured("google")
    max_keys = config.MAX_GOOGLE_KEYS

    new_values = []
    for slot in range(max_keys):
        if slot == 0:
            field_label = "Primary key (GOOGLE_API_KEY)"
        else:
            field_label = (
                f"Additional key {slot + 1} (GOOGLE_API_KEY_{slot + 1}) — optional"
            )
        value = st.text_input(
            field_label,
            type="password",
            key=f"google_key_{slot}",
            placeholder="Paste your Gemini API key here",
        )
        new_values.append(value)

    st.caption(
        "Add more than one key only if you process very large datasets and "
        "want to spread the load across separate Gemini quotas."
    )
    remember = st.checkbox("Remember on this computer", key="remember_google")
    col1, col2, col3 = st.columns(3)
    if col1.button("Use key(s)", key="use_google"):
        cleaned = [v.strip() for v in new_values if v and v.strip()]
        if not cleaned:
            st.warning("Enter at least one key first.")
            return
        if remember:
            config.save_google_api_keys(cleaned)
            for env_var in _google_env_vars():
                _session_keys().pop(env_var, None)
            st.success("Saved for future sessions.")
        else:
            _set_session_google_api_keys(cleaned)
            st.success("Using key(s) for this session.")
        st.rerun()
    if _provider_session_configured("google") and col2.button(
        "Forget session", key="clear_session_google"
    ):
        _clear_session_google_api_keys()
        st.rerun()
    if saved and col3.button("Clear saved", key="clear_google"):
        config.save_google_api_keys([])
        for env_var in _google_env_vars():
            if env_var in _session_keys():
                os.environ[env_var] = _session_keys()[env_var]
        st.rerun()


def _render_local_model_setup():
    """Show local/Ollama setup status in the sidebar from every page."""
    installed = get_ollama_models_cached(timeout=0.35)
    badge = f"{len(installed)} installed" if installed else "Setup needed"
    with st.sidebar.expander(f"Local models (Ollama) — {badge}", expanded=False):
        if installed:
            st.caption(
                "Ollama is running. These models can appear under "
                "**Model source → Local Ollama** after you choose a dataset."
            )
            for model_info in installed[:8]:
                st.markdown(f"- {_ollama_model_sidebar_label(model_info)}")
            remaining = len(installed) - 8
            if remaining > 0:
                st.caption(f"...and {remaining} more.")
        else:
            st.warning("Ollama is not running, or no local models are installed.")
            st.markdown("[Install Ollama](https://ollama.com/download)")
            st.code("ollama pull qwen3:8b", language="bash")
            st.caption(
                "After installing Ollama and pulling a model, refresh this GUI "
                "and choose **Local Ollama** in step 2."
            )
        if st.button("Refresh local models", key="refresh_local_models"):
            clear_ollama_cache()
            st.rerun()


def render_sidebar():
    config = get_config()

    logo = get_logo_path()
    if logo:
        st.sidebar.image(logo, width=140)

    page = st.sidebar.radio(
        "Go to",
        ["Process data", "Batch downloads", "Ensemble analysis"],
        label_visibility="collapsed",
        key="page",
    )

    st.sidebar.divider()
    st.sidebar.caption("**API keys** — cloud models only; local models need none.")

    for provider, label in PROVIDERS:
        saved = _provider_saved_configured(provider)
        session = _provider_session_configured(provider)
        available = _provider_available(config, provider)
        if session:
            badge = "Session"
        elif saved:
            badge = "Saved"
        elif available:
            badge = "Environment"
        else:
            badge = "Not set"
        with st.sidebar.expander(
            f"{label} — {badge}", expanded=not (saved or session or available)
        ):
            st.caption(
                "Used for this session only unless you tick "
                "**Remember on this computer**."
            )
            if provider == "google":
                _render_google_keys(config)
            else:
                _render_single_key(config, provider, label, saved)

    _render_local_model_setup()

    st.sidebar.caption(f"Data folder: `{get_output_dir()}`")
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Open folder", key="sidebar_open_folder"):
        if open_in_file_manager(str(get_output_dir())):
            st.toast("Opened output folder in your file browser.")
        else:
            st.sidebar.warning("Could not open the folder. Copy the path above.")
    if col2.button("Start over"):
        for k in [
            "selected_dataset",
            "dataset_records",
            "_dataset_cache",
            "mode",
            "model_file",
            "formats",
            "use_dwc",
            "batch_size",
            "processing_requested",
            "run_results",
        ]:
            st.session_state.pop(k, None)
        st.rerun()

    return page


# ---------------------------------------------------------------------------
# Section 1: choose / upload a dataset
# ---------------------------------------------------------------------------


def _render_dataset_section(dataset_manager: DatasetManager):
    st.header("1 · Choose your data")
    st.write(
        "Upload a spreadsheet of localities (CSV or TSV), or pick one already "
        "in your input folder. It needs an **ID** column and a **locality "
        "description** column."
    )

    uploaded = st.file_uploader("Upload a CSV or TSV file", type=["csv", "tsv", "txt"])
    if uploaded is not None:
        upload_name = _safe_uploaded_filename(uploaded.name)
        dest = os.path.join(str(get_input_dir()), upload_name)
        with open(dest, "wb") as f:
            f.write(uploaded.getbuffer())
        st.success(f"Uploaded **{upload_name}**")

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
            if d["filename"] == upload_name:
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
    records = _dataset_records_cached(dataset_manager, selected)
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

    # Commit the selection so section 2 appears below; if the dataset changed,
    # invalidate any processing section from a previous run.
    prev = st.session_state.get("selected_dataset")
    changed = prev is not None and (
        (prev["filename"], prev["row_count"])
        != (selected["filename"], selected["row_count"])
    )
    st.session_state.selected_dataset = selected
    st.session_state.dataset_records = records
    if changed:
        st.session_state.processing_requested = False
        st.session_state.pop("run_results", None)


# ---------------------------------------------------------------------------
# Section 2: configure (mode, model, formats) + cost estimate
# ---------------------------------------------------------------------------


@st.fragment
def _render_configure_section():
    # A fragment so toggling widgets here (mode, model table, formats, DwC)
    # reruns only this section, not the dataset preview or sidebar. Anything
    # that must update the rest of the page uses st.rerun(scope="app").
    selected = st.session_state.selected_dataset
    num_records = selected["row_count"]

    st.header("2 · Choose how to process")
    st.caption(f"Dataset: **{selected['filename']}** · {num_records:,} records")

    # --- Mode ---
    mode_options = {
        "Real-time (results now)": "realtime",
        "Batch (cheaper, up to 24h)": "batch",
        "Staggered batch (very large / quota-safe)": "staggered",
    }
    mode_label = st.radio(
        "Processing mode",
        list(mode_options.keys()),
        help="Real-time is best for small datasets (under ~1,000 records). "
        "Batch is ~50% cheaper and returns within 24h. Staggered batch is for "
        "very large jobs (3,000+): it splits the data into several smaller "
        "batches submitted with delays so you stay under provider quotas.",
    )
    mode = mode_options[mode_label]
    # Staggered uses the same batch pricing (50% discount) for estimates.
    cost_mode = "batch" if mode in ("batch", "staggered") else "realtime"
    if mode == "staggered":
        st.info(
            "Staggered mode splits your dataset into provider-sized sub-batches "
            "and submits them with delays (10–120s each) to avoid quota limits. "
            "Submission can take a few minutes for very large jobs; keep this "
            "tab open until it finishes. Results are fetched later from "
            "**Batch downloads**."
        )

    # --- Model selection with comparison table ---
    configs = load_all_model_profiles(include_dynamic_ollama=True)
    if not configs:
        st.error("No model profiles found.")
        return

    comparisons = ModelComparison.compare_models(configs, num_records, cost_mode)
    comp_by_name = {c["model_name"]: c for c in comparisons}

    import pandas as pd

    st.subheader("Available models")
    st.caption(
        "Use the local picker for installed Ollama models, or the table for "
        "cloud/API models. Cloud models need an API key; local models need "
        "Ollama running and the selected model installed."
    )

    file_by_index = [cfg["_file"] for cfg in configs]
    ready_files = [c["_file"] for c in configs if _model_has_key(c)]
    local_configs = [c for c in configs if is_local_model_config(c)]
    cloud_configs = [c for c in configs if not is_local_model_config(c)]
    if not ready_files:
        st.warning(
            "No models are ready. Add an API key in the sidebar, or "
            "start Ollama and install a local model."
        )
        if local_configs:
            with st.expander("Local model status"):
                for cfg in local_configs:
                    st.write(
                        f"- **{cfg.get('name', cfg.get('_file'))}**: "
                        f"{cfg.get('local_status', 'Unavailable')} "
                        f"`{cfg.get('local_status_detail', '')}`"
                    )
        return

    # Persist the chosen model across reruns; default to the first ready model.
    prev = st.session_state.get("model_file")
    if prev not in file_by_index:
        prev = ready_files[0]

    source = st.radio(
        "Model source",
        ["All models", "Local Ollama", "Cloud/API"],
        horizontal=True,
        key="model_source",
    )

    selected_file = prev
    if source == "Local Ollama":
        if not local_configs:
            st.warning(
                "No local Ollama profiles were found. Start Ollama and install "
                "a model such as `ollama pull qwen3:8b`, then refresh this page."
            )
            return

        local_files = [cfg["_file"] for cfg in local_configs]
        local_ready = [cfg for cfg in local_configs if _model_has_key(cfg)]
        default_local_file = prev if prev in local_files else local_files[0]
        default_local_idx = local_files.index(default_local_file)
        selected_local_idx = st.selectbox(
            "Local Ollama model",
            range(len(local_configs)),
            format_func=lambda i: _model_select_label(local_configs[i]),
            index=default_local_idx,
            key="local_model_picker",
            help=(
                "Shows installed Ollama models plus bundled local profiles. "
                "Only installed models can run."
            ),
        )
        selected_file = local_configs[selected_local_idx]["_file"]
        st.session_state.model_file = selected_file

        if local_ready:
            st.caption(
                f"{len(local_ready)} local model(s) ready. Local processing "
                "does not send locality text to a cloud API."
            )
        with st.expander("Local model status", expanded=not local_ready):
            for cfg in local_configs:
                st.write(
                    f"- **{cfg.get('name', cfg.get('_file'))}**: "
                    f"{cfg.get('local_status', _model_ready_label(cfg))} "
                    f"`{cfg.get('local_status_detail', '')}`"
                )
    else:
        table_configs = cloud_configs if source == "Cloud/API" else configs
        table_files = [cfg["_file"] for cfg in table_configs]
        if prev not in table_files:
            ready_table_files = [c["_file"] for c in table_configs if _model_has_key(c)]
            selected_file = (
                ready_table_files[0] if ready_table_files else table_files[0]
            )

        rows = []
        for cfg in table_configs:
            comp = comp_by_name.get(cfg.get("name", ""), {})
            rows.append(
                {
                    "Use": cfg["_file"] == selected_file,
                    "Model": cfg.get("name", cfg.get("_file")),
                    "Vendor": comp.get("vendor", cfg.get("provider", "")),
                    "Model ID": cfg.get("model_id", ""),
                    "Est. cost": (
                        "Free"
                        if comp.get("is_local")
                        else f"${comp.get('estimated_cost', 0):.4f}"
                    ),
                    "Est. time (min)": comp.get("estimated_time_minutes", "—"),
                    "Ready": _model_ready_label(cfg),
                }
            )

        edited = st.data_editor(
            pd.DataFrame(rows),
            hide_index=True,
            use_container_width=True,
            disabled=[
                "Model",
                "Vendor",
                "Model ID",
                "Est. cost",
                "Est. time (min)",
                "Ready",
            ],
            column_config={
                "Use": st.column_config.CheckboxColumn(
                    "Use",
                    help="Select this single model to run",
                    default=False,
                ),
            },
            # Re-key on the current source/selection so the editor's accumulated
            # edit state resets whenever the chosen model changes.
            key=f"model_table_{source}_{selected_file}",
        )

        # The checkbox column behaves like a radio: resolve a single selection,
        # preferring any newly-ticked row over the previous choice.
        checked = [i for i in edited.index if bool(edited.loc[i, "Use"])]
        if checked:
            newly = [table_files[i] for i in checked if table_files[i] != selected_file]
            selected_file = newly[0] if newly else table_files[checked[0]]
        st.session_state.model_file = selected_file

    model_file = selected_file
    model_config = next(c for c in configs if c["_file"] == model_file)

    if not _model_has_key(model_config):
        if is_local_model_config(model_config):
            st.warning(
                f"**{model_config.get('name', model_file)}** is not ready: "
                f"{model_config.get('local_status', 'local model unavailable')}. "
                f"{model_config.get('local_status_detail', '')}"
            )
        else:
            st.warning(
                f"**{model_config.get('name', model_file)}** needs an API key. "
                "Add one in the sidebar, then it will be ready to run."
            )
        return

    # --- Cost estimate ---
    cost = CostEstimator.estimate_cost(
        num_records,
        model_config,
        processing_mode=cost_mode,
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
    use_dwc = st.checkbox(
        "Use Darwin Core (DwC) output terms",
        value=st.session_state.get("use_dwc", False),
        help=(
            "Rename output columns to Darwin Core terms (dwc.tdwg.org), "
            "e.g. Latitude → decimalLatitude, Exact_Site → locality."
        ),
    )
    deduplicate = st.checkbox(
        "Deduplicate repeated localities before processing",
        value=st.session_state.get("deduplicate", True),
        help=(
            "Georeference each unique locality/country once instead of every "
            "duplicate (saves time and cost). Results are automatically "
            "re-expanded onto every original record."
        ),
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

    if st.button("Start processing →", type="primary"):
        # Snapshot the chosen settings so later widget fiddling in this
        # section cannot change a run that is already in flight.
        st.session_state.mode = mode
        st.session_state.model_file = model_file
        st.session_state.formats = formats or ["csv"]
        st.session_state.use_dwc = bool(use_dwc)
        st.session_state.deduplicate = bool(deduplicate)
        st.session_state.batch_size = int(batch_size)
        st.session_state.processing_requested = True
        st.session_state.pop("run_results", None)
        st.session_state._scroll_to_processing = True
        # scope="app": a fragment-scoped rerun would never show section 3.
        st.rerun(scope="app")


# ---------------------------------------------------------------------------
# Section 3: run + results
# ---------------------------------------------------------------------------


def _render_processing_section(dataset_manager: DatasetManager):
    selected = st.session_state.selected_dataset
    mode = st.session_state.mode
    model_config = load_model_profile(st.session_state.model_file)

    st.header("3 · Processing", anchor="processing")
    if model_config is None:
        st.error(
            "The selected model is no longer available. Pick another model "
            "in section 2 and start again."
        )
        return
    st.caption(
        f"Dataset: **{selected['filename']}** · Mode: {mode} · "
        f"Model: {model_config.get('name', st.session_state.model_file)}"
    )

    # One-shot smooth scroll down to this section after Start is clicked.
    if st.session_state.pop("_scroll_to_processing", False):
        import streamlit.components.v1 as components

        components.html(
            "<script>parent.document.getElementById('processing')"
            "?.scrollIntoView({behavior:'smooth'});</script>",
            height=0,
        )

    if "run_results" not in st.session_state:
        if mode == "realtime":
            _run_realtime(dataset_manager, selected, model_config)
        elif mode == "staggered":
            _run_staggered(selected, model_config)
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
                deduplicate=st.session_state.get("deduplicate", True),
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
        use_dwc = st.session_state.get("use_dwc", False)
        if records and tsv_path:
            base_path = os.path.splitext(tsv_path)[0]
            saved_files = OutputFormatter.write_output(records, base_path, formats, dwc=use_dwc)

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
    deduplicate = st.session_state.get("deduplicate", True)
    if deduplicate:
        from placebot.core.deduplication import deduplicate_records
        original_count = len(records)
        records, duplicates_removed = deduplicate_records(records)
        st.info(
            f"Deduplicated {original_count:,} → {len(records):,} unique localities "
            f"({duplicates_removed:,} duplicate rows collapsed). Results will be "
            "re-expanded onto every original record when you download them."
        )
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
        "use_dwc": st.session_state.get("use_dwc", False),
        "deduplicated": deduplicate,
    }
    info_file = os.path.join(batch_dir, f"{batch_name}_info.json")
    with open(info_file, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

    st.session_state.run_results = {
        "type": "batch",
        "batch_id": batch_id,
        "info_file": info_file,
    }


# Provider-tuned sub-batch sizes and inter-submission delays (seconds),
# mirroring the CLI's staggered mode so quotas aren't exceeded.
_STAGGER_PROFILE = {
    "gemini": (500, 120),
    "google": (500, 120),
    "anthropic": (1000, 30),
    "openai": (2000, 10),
    "gpt": (2000, 10),
}


def _stagger_profile(provider: str):
    for key, prof in _STAGGER_PROFILE.items():
        if key in provider:
            return prof
    return None


def _run_staggered(selected, model_config):
    import time

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
            f"Staggered batch is not supported for provider '{provider}'. "
            "Use Real-time mode instead."
        )
        return

    profile = _stagger_profile(provider)
    if profile is None:
        st.error(f"No staggered profile for provider '{provider}'.")
        return
    batch_size, delay_seconds = profile

    records = st.session_state.dataset_records
    deduplicate = st.session_state.get("deduplicate", True)
    if deduplicate:
        from placebot.core.deduplication import deduplicate_records
        original_count = len(records)
        records, duplicates_removed = deduplicate_records(records)
        st.info(
            f"Deduplicated {original_count:,} → {len(records):,} unique localities "
            f"({duplicates_removed:,} duplicate rows collapsed). Results will be "
            "re-expanded onto every original record when you download them."
        )
    prompt_template = AIProcessor(model_config)._get_full_instructions()
    total_records = len(records)
    num_batches = (total_records + batch_size - 1) // batch_size

    batch_dir = os.path.join(str(get_output_dir()), "batch_jobs")
    os.makedirs(batch_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = os.path.splitext(selected["filename"])[0]
    model_safe = model_config.get("name", "model").replace(" ", "_")
    batch_name = f"{stem}_{model_safe}_{timestamp}"
    output_formats = st.session_state.formats

    st.write(
        f"Submitting **{num_batches}** sub-batch(es) of up to {batch_size:,} "
        f"records, with a {delay_seconds}s pause between each."
    )
    bar = st.progress(0.0)
    status = st.empty()

    batch_info_list = []
    submit_error = None
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, total_records)
        batch_records = records[start_idx:end_idx]
        sub_batch_name = f"{batch_name}_batch{batch_num + 1}of{num_batches}"

        status.write(
            f"Submitting sub-batch {batch_num + 1}/{num_batches} "
            f"(records {start_idx + 1}–{end_idx})…"
        )
        try:
            if "openai" in provider or "gpt" in provider:
                batch_file = os.path.join(batch_dir, f"{sub_batch_name}.jsonl")
                bp.prepare_batch_file(batch_records, prompt_template, batch_file)
                sub_batch_id = bp.submit_batch(batch_file, sub_batch_name)
            else:
                requests_list = bp.prepare_batch_requests(
                    batch_records, prompt_template
                )
                sub_batch_id = bp.submit_batch(requests_list, sub_batch_name)
        except Exception as e:
            submit_error = str(e)
            status.write(f"Sub-batch {batch_num + 1} failed: {e}")
            break

        sub_info = {
            "batch_number": batch_num + 1,
            "total_batches": num_batches,
            "batch_id": sub_batch_id,
            "batch_name": sub_batch_name,
            "provider": provider,
            "model": model_id,
            "dataset": selected["filename"],
            "start_record": start_idx + 1,
            "end_record": end_idx,
            "record_count": end_idx - start_idx,
            "submitted_at": timestamp,
            "output_formats": output_formats,
            "use_dwc": st.session_state.get("use_dwc", False),
            "deduplicated": deduplicate,
        }
        batch_info_list.append(sub_info)
        with open(
            os.path.join(batch_dir, f"{sub_batch_name}_info.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(sub_info, f, indent=2, ensure_ascii=False)

        bar.progress((batch_num + 1) / num_batches)

        # Pause before the next submission (not after the last one).
        if batch_num < num_batches - 1:
            status.write(
                f"Submitted {batch_num + 1}/{num_batches}. "
                f"Waiting {delay_seconds}s before the next sub-batch…"
            )
            time.sleep(delay_seconds)

    summary = {
        "total_records": total_records,
        "batch_size": batch_size,
        "batches_submitted": len(batch_info_list),
        "provider": provider,
        "model": model_id,
        "dataset": selected["filename"],
        "submitted_at": timestamp,
        "output_formats": output_formats,
        "use_dwc": st.session_state.get("use_dwc", False),
        "deduplicated": deduplicate,
        "batches": batch_info_list,
    }
    summary_file = os.path.join(batch_dir, f"{batch_name}_staggered_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    bar.progress(1.0)
    st.session_state.run_results = {
        "type": "staggered",
        "summary_file": summary_file,
        "batches_submitted": len(batch_info_list),
        "num_batches": num_batches,
        "submit_error": submit_error,
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

    if res["type"] == "staggered":
        n = res["batches_submitted"]
        total = res["num_batches"]
        if res.get("submit_error") and n < total:
            st.warning(
                f"Submitted {n} of {total} sub-batches before an error: "
                f"{res['submit_error']}. The submitted sub-batches will still "
                "process; you can fetch their results from **Batch downloads**."
            )
        else:
            st.success(f"Staggered batch submitted! {n} sub-batch(es) queued.")
        st.write(
            "Each sub-batch completes independently within 24 hours. When "
            "they're done, open **Batch downloads** in the sidebar to fetch "
            "and merge all results — no command line needed."
        )
        st.caption(f"Summary saved to: {res['summary_file']}")
        return

    results = res["results"]
    if not results.get("success"):
        st.error(
            f"Processing did not complete: {results.get('error', 'unknown error')}"
        )
        return

    records = results.get("processed_records", [])
    counts = _processing_counts(records)
    if counts["failed"] == counts["total"] and counts["total"]:
        st.error(
            f"Processing finished, but all {counts['total']:,} records failed. "
            "Check `Processing_Notes` in the table/output files before using "
            "these results."
        )
    elif counts["failed"]:
        st.warning(
            f"Processed {counts['total']:,} records with "
            f"{counts['failed']:,} failure(s). Check `Processing_Notes` for "
            "the affected rows."
        )
    else:
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
        dwc=st.session_state.get("use_dwc", False),
    )


# ---------------------------------------------------------------------------
# Batch downloads page
# ---------------------------------------------------------------------------


def _list_batch_jobs():
    """Return submitted batch jobs (newest first) from the batch_jobs folder.

    Includes both single async batches (``*_info.json``) and staggered jobs
    (``*_staggered_summary.json``). Sub-batch info files belonging to a
    staggered job are skipped - the summary represents them.
    """
    batch_dir = str(get_batch_jobs_dir())
    jobs = []
    if not os.path.isdir(batch_dir):
        return jobs

    for fname in os.listdir(batch_dir):
        path = os.path.join(batch_dir, fname)
        try:
            if os.path.getsize(path) == 0:
                continue
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        if fname.endswith("_staggered_summary.json"):
            jobs.append(
                {
                    "type": "staggered",
                    "label": fname.replace("_staggered_summary.json", ""),
                    "summary_file": path,
                    "provider": data.get("provider", ""),
                    "model": data.get("model", ""),
                    "record_count": data.get("total_records", 0),
                    "submitted_at": data.get("submitted_at", ""),
                    "output_formats": data.get("output_formats", ["csv"]),
                    "use_dwc": data.get("use_dwc", False),
                    "dataset": data.get("dataset", ""),
                    "deduplicated": data.get("deduplicated", False),
                    "batches_submitted": data.get(
                        "batches_submitted", len(data.get("batches", []))
                    ),
                }
            )
        elif fname.endswith("_info.json"):
            # Sub-batches of a staggered job carry 'batch_number'; skip them.
            if "batch_number" in data or "batch_id" not in data:
                continue
            data["type"] = "single"
            data["label"] = data.get("batch_name", data["batch_id"])
            jobs.append(data)

    jobs.sort(key=lambda i: i.get("submitted_at", ""), reverse=True)
    return jobs


def step_batch_downloads():
    from placebot.cli.batch_download import fetch_batch_results
    from placebot.cli.batch_download_staggered import fetch_staggered_results

    st.header("Batch downloads")
    st.write(
        "Submitted a batch job? Once it finishes (usually within 24 hours) "
        "fetch and download the results here — no command line required."
    )

    jobs = _list_batch_jobs()
    if not jobs:
        st.info(
            "No batch jobs found yet. Submit one from **Process data** using "
            "the *Batch* or *Staggered batch* processing mode."
        )
        return

    def _label(i):
        j = jobs[i]
        tag = "staggered" if j["type"] == "staggered" else "batch"
        return (
            f"[{tag}] {j['label']} — {j.get('record_count', 0):,} records, "
            f"submitted {j.get('submitted_at', '?')}"
        )

    idx = st.selectbox("Select a batch job", range(len(jobs)), format_func=_label)
    job = jobs[idx]
    job_key = job.get("summary_file") or job.get("batch_id")

    c1, c2, c3 = st.columns(3)
    c1.metric("Provider", job.get("provider", "—"))
    c2.metric("Records", f"{job.get('record_count', 0):,}")
    c3.metric("Model", job.get("model", "—"))
    if job["type"] == "staggered":
        st.caption(f"Sub-batches: {job.get('batches_submitted', 0)}")
    else:
        st.caption(f"Batch ID: `{job['batch_id']}`")

    if st.button("Download results", type="primary"):
        with st.spinner("Fetching results from the provider…"):
            if job["type"] == "staggered":
                result = fetch_staggered_results(job["summary_file"])
            else:
                result = fetch_batch_results(job["batch_id"])
        result["_job_key"] = job_key
        st.session_state.batch_dl_result = result

    result = st.session_state.get("batch_dl_result")
    # Only show results for the currently-selected job
    if not result or result.get("_job_key") != job_key:
        return

    if not result["success"]:
        st.warning(result["error"])
        return

    records = result["records"]
    formats = job.get("output_formats") or ["csv"]
    use_dwc = bool(job.get("use_dwc", False))
    stem = job["label"] + ("_merged" if job["type"] == "staggered" else "")

    # If the job was deduplicated at submission, re-expand the results onto every
    # original record by reloading the source file (joined on locality+country).
    if job.get("deduplicated"):
        from placebot.cli.batch_manager import _load_source_record_list
        from placebot.core.deduplication import reconstitute_records

        original_records = _load_source_record_list(job.get("dataset"))
        if original_records:
            records, expand_stats = reconstitute_records(original_records, records)
            st.caption(
                f"Re-expanded onto {expand_stats['total']:,} original records "
                f"({expand_stats['matched']:,} matched a georeference)."
            )
        else:
            st.warning(
                "This job was deduplicated, but the original input file is no "
                "longer in your input folder, so results stay deduplicated. "
                "Re-add the source file and download again to re-expand."
            )

    if job["type"] == "staggered":
        expected = result.get("expected", 0)
        failed = result.get("failed", [])
        st.caption(
            f"Merged {len(records):,} of {expected:,} expected records"
            + (f" · {len(failed)} sub-batch(es) not ready yet" if failed else "")
        )

    # Auto-save the chosen formats into the output folder, matching real-time
    # mode (same canonical columns and UTF-8 BOM on CSV). Done once per fetch.
    saved_files = result.get("saved_files")
    if saved_files is None:
        base_path = os.path.join(str(get_output_dir()), stem)
        saved_files = OutputFormatter.write_output(records, base_path, formats, dwc=use_dwc)
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
        dwc=use_dwc,
    )


# ---------------------------------------------------------------------------
# Ensemble analysis page
# ---------------------------------------------------------------------------


def _list_output_files():
    """Return comparable output files under the output folder (newest first).

    Scans recursively (results land in dated sub-folders) for CSV/TSV/TXT/JSON,
    skipping progress files, READMEs, GeoJSON, and batch-job metadata.
    """
    out_dir = str(get_output_dir())
    valid_exts = (".csv", ".tsv", ".txt", ".json")
    found = []
    for root, _dirs, files in os.walk(out_dir):
        if "batch_jobs" in root:
            continue
        for name in files:
            lower = name.lower()
            if not lower.endswith(valid_exts):
                continue
            if lower in ("readme.txt",) or lower.endswith("_progress.tsv"):
                continue
            path = os.path.join(root, name)
            try:
                if os.path.getsize(path) == 0:
                    continue
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            found.append((path, mtime))
    found.sort(key=lambda t: t[1], reverse=True)
    return [p for p, _ in found]


def step_ensemble_analysis():
    from placebot.core.ensemble_analysis import CATEGORIES, run_ensemble

    st.header("Ensemble analysis")
    st.write(
        "Ran the same dataset through two models? Compare their coordinates "
        "here. Records are matched on **Barcode**, and each gets an agreement "
        "category and the distance (km) between the two estimates so you can "
        "filter records for manual verification."
    )

    # Optional: bring in an external output file (CSV/TSV/JSON).
    with st.expander("Upload an output file (optional)"):
        uploaded = st.file_uploader(
            "Add a CSV/TSV/JSON output file to the comparison list",
            type=["csv", "tsv", "txt", "json"],
            key="ensemble_upload",
        )
        if uploaded is not None:
            upload_name = _safe_uploaded_filename(uploaded.name)
            dest = os.path.join(str(get_output_dir()), upload_name)
            with open(dest, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success(f"Added **{upload_name}** to your output folder.")

    files = _list_output_files()
    if len(files) < 2:
        st.info(
            "Need at least two output files to compare. Run two models on the "
            "same dataset from **Process data**, or upload files above."
        )
        return

    out_dir = str(get_output_dir())

    def _label(path):
        try:
            return os.path.relpath(path, out_dir)
        except ValueError:
            return path

    c1, c2 = st.columns(2)
    primary = c1.selectbox(
        "Primary file (values carried forward)",
        files,
        format_func=_label,
        key="ensemble_primary",
    )
    secondary = c2.selectbox(
        "Secondary file (compared against)",
        files,
        index=1 if len(files) > 1 else 0,
        format_func=_label,
        key="ensemble_secondary",
    )

    if primary == secondary:
        st.warning("Pick two different files to compare.")
        return

    pair_key = f"{primary}|{secondary}"

    if st.button("Run comparison", type="primary"):
        with st.spinner("Comparing the two outputs…"):
            try:
                result = run_ensemble(primary, secondary)
            except Exception as e:  # surface parse/IO errors to the user
                result = {"error": str(e)}
        result["_pair_key"] = pair_key
        st.session_state.ensemble_result = result

    result = st.session_state.get("ensemble_result")
    # Only show results for the currently-selected pair.
    if not result or result.get("_pair_key") != pair_key:
        return

    if result.get("error"):
        st.error(f"Could not compare those files: {result['error']}")
        return

    records = result["records"]
    total = result["total"]
    if not records:
        st.warning("No records to compare (empty or unreadable files).")
        return

    st.success(f"Compared {total:,} records.")

    # Per-category counts.
    cols = st.columns(len(CATEGORIES))
    for col, cat in zip(cols, CATEGORIES):
        col.metric(cat, f"{result['summary'].get(cat, 0):,}")

    notes = []
    if result["only_in_primary"]:
        notes.append(
            f"{result['only_in_primary']:,} barcode(s) only in the primary file"
        )
    if result["only_in_secondary"]:
        notes.append(f"{result['only_in_secondary']:,} only in the secondary file")
    if result["duplicate_barcodes"]:
        notes.append(
            f"{result['duplicate_barcodes']:,} duplicate barcode(s) in the secondary file (ignored)"
        )
    if notes:
        st.caption(" · ".join(notes))

    # Auto-save TSV + CSV into the output folder (cached on the result).
    formats = ["tsv", "csv"]
    stem = (
        f"ensemble_{os.path.splitext(os.path.basename(primary))[0]}"
        f"_vs_{os.path.splitext(os.path.basename(secondary))[0]}"
    )
    column_order = result.get("column_order")
    saved_files = result.get("saved_files")
    if saved_files is None:
        base_path = os.path.join(out_dir, stem)
        saved_files = OutputFormatter.write_output(
            records, base_path, formats, column_order=column_order
        )
        result["saved_files"] = saved_files

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
        key_prefix="ensemble",
        heading="Or download a copy",
        column_order=column_order,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _page_process(dataset_manager: DatasetManager) -> None:
    """Single scrolling 'Process data' page: sections 1 → 2 → 3.

    All visible sections render top-to-bottom on every rerun, so moving
    between them never blanks the page (unlike the old step wizard).
    Section 2 appears once a dataset is selected; section 3 once the user
    clicks Start processing.
    """
    _render_dataset_section(dataset_manager)
    if st.session_state.get("selected_dataset"):
        st.divider()
        _render_configure_section()
    if st.session_state.get("processing_requested"):
        st.divider()
        _render_processing_section(dataset_manager)


def main():
    logo = get_logo_path()
    st.set_page_config(
        page_title="PlaceBot",
        page_icon=logo or "🌍",
        layout="wide",
    )
    setup_directories()

    header_cols = st.columns([1, 5, 1])
    if logo:
        header_cols[0].image(logo, width=90)
    with header_cols[1]:
        st.title("PlaceBot")
        st.caption("Turn locality descriptions into geographic coordinates.")
    with header_cols[2]:
        st.write("")
        if st.button("How to use", key="toggle_how_to_use"):
            st.session_state.show_how_to_use = not st.session_state.get(
                "show_how_to_use", False
            )

    if st.session_state.get("show_how_to_use", False):
        _render_how_to_use_panel()
        st.divider()

    page = render_sidebar()

    if page == "Batch downloads":
        step_batch_downloads()
        return

    if page == "Ensemble analysis":
        step_ensemble_analysis()
        return

    dataset_manager = DatasetManager(
        input_folder=str(get_input_dir()),
        output_folder=str(get_output_dir()),
    )
    _page_process(dataset_manager)


# Streamlit executes this script with __name__ == "__main__".
if __name__ == "__main__":
    main()
