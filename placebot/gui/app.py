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

import io
import json
import os
from datetime import datetime

import streamlit as st

from placebot.core.config import get_config
from placebot.core.data_dirs import (
    setup_directories,
    get_input_dir,
    get_output_dir,
)
from placebot.core.file_manager import DatasetManager, OutputManager
from placebot.core.dataset_preview import DatasetPreview
from placebot.core.model_selector import discover_models, load_model_profile
from placebot.core.model_comparison import ModelComparison
from placebot.core.cost_estimator import CostEstimator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROVIDERS = [
    ("anthropic", "Anthropic (Claude)"),
    ("openai", "OpenAI (GPT)"),
    ("google", "Google (Gemini)"),
]


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


def records_to_csv_bytes(records: list) -> bytes:
    import csv

    if not records:
        return b""
    fieldnames = []
    for r in records:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue().encode("utf-8")


def records_to_json_bytes(records: list) -> bytes:
    return json.dumps(records, indent=2, ensure_ascii=False).encode("utf-8")


def records_to_geojson_bytes(records: list) -> bytes:
    """Build GeoJSON, handling PlaceBot's capitalised Latitude/Longitude keys."""
    features = []
    for r in records:
        lat = r.get("Latitude") or r.get("latitude") or r.get("lat")
        lon = r.get("Longitude") or r.get("longitude") or r.get("lon")
        if lat in (None, "") or lon in (None, ""):
            continue
        try:
            lat_f, lon_f = float(lat), float(lon)
        except (ValueError, TypeError):
            continue
        props = {
            k: v
            for k, v in r.items()
            if k not in ("Latitude", "latitude", "lat", "Longitude", "longitude", "lon")
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon_f, lat_f]},
                "properties": props,
            }
        )
    geojson = {"type": "FeatureCollection", "features": features}
    return json.dumps(geojson, indent=2, ensure_ascii=False).encode("utf-8")


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


def render_sidebar():
    st.sidebar.header("🔑 API Keys")
    st.sidebar.caption(
        "Keys are saved to `~/.placebot/.env` on your computer and remembered "
        "between sessions. Local (Qwen/Ollama) models need no key."
    )

    config = get_config()
    status = config.check_api_keys()

    for provider, label in PROVIDERS:
        configured = status.get(provider, False)
        badge = "✅ Configured" if configured else "⚠️ Not set"
        with st.sidebar.expander(f"{label} — {badge}", expanded=not configured):
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

    st.sidebar.divider()
    st.sidebar.caption(f"📂 Data folder: `{get_output_dir()}`")
    if st.sidebar.button("↩️ Start over"):
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

    st.subheader("Available models")
    rows = []
    for cfg in configs:
        comp = comp_by_name.get(cfg.get("name", ""), {})
        ready = _model_has_key(cfg)
        rows.append(
            {
                "Model": cfg.get("name", cfg.get("_file")),
                "Vendor": comp.get("vendor", cfg.get("provider", "")),
                "Est. cost": (
                    "Free"
                    if comp.get("is_local")
                    else f"${comp.get('estimated_cost', 0):.4f}"
                ),
                "Est. time (min)": comp.get("estimated_time_minutes", "—"),
                "Ready": "✅" if ready else "🔑 needs key",
            }
        )
    try:
        import pandas as pd

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    except Exception:
        st.table(rows)

    ready_files = [c["_file"] for c in configs if _model_has_key(c)]
    if not ready_files:
        st.warning(
            "No models are ready. Add an API key in the sidebar, or "
            "install a local Qwen model."
        )
        return

    def _label(file_name):
        cfg = next(c for c in configs if c["_file"] == file_name)
        return cfg.get("name", file_name)

    model_file = st.selectbox("Pick a model to use", ready_files, format_func=_label)
    model_config = next(c for c in configs if c["_file"] == model_file)

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
    st.session_state.run_results = {"type": "realtime", "results": results}


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
        st.success("✅ Batch submitted!")
        st.write(f"**Batch ID:** `{res['batch_id']}`")
        st.write(
            "Your results will be ready within 24 hours (usually much "
            "faster). Download them later from the command line:"
        )
        st.code(f"placebot-batch download {res['batch_id']}")
        st.caption(f"Job details saved to: {res['info_file']}")
        return

    results = res["results"]
    if not results.get("success"):
        st.error(
            f"Processing did not complete: {results.get('error', 'unknown error')}"
        )
        return

    records = results.get("processed_records", [])
    st.success(f"✅ Done! Processed {len(records):,} records.")
    st.caption(f"Results also saved to: {results.get('output_path', '')}")

    with st.expander("Summary report"):
        st.text(results.get("summary_report", ""))

    try:
        import pandas as pd

        st.dataframe(pd.DataFrame(records), use_container_width=True)
    except Exception:
        st.write(records[:50])

    st.subheader("Download")
    formats = st.session_state.get("formats", ["csv"])
    cols = st.columns(len(formats))
    builders = {
        "csv": ("text/csv", "csv", records_to_csv_bytes),
        "json": ("application/json", "json", records_to_json_bytes),
        "geojson": ("application/geo+json", "geojson", records_to_geojson_bytes),
    }
    stem = os.path.splitext(st.session_state.selected_dataset["filename"])[0]
    for col, fmt in zip(cols, formats):
        mime, ext, builder = builders[fmt]
        col.download_button(
            f"⬇️ {fmt.upper()}",
            data=builder(records),
            file_name=f"{stem}_placebot.{ext}",
            mime=mime,
            key=f"dl_{fmt}",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    st.set_page_config(page_title="PlaceBot", page_icon="🌍", layout="wide")
    setup_directories()

    st.title("🌍 PlaceBot")
    st.caption("Turn locality descriptions into geographic coordinates.")

    render_sidebar()

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
