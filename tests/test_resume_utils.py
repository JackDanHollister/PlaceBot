"""Tests for resume-state persistence.

Regression coverage for the bug where resume state was written to a bare
relative ``output/`` directory, which fails with a permission error on
Windows when PlaceBot is launched from a non-writable working directory.
"""

import os

from placebot.core import resume_utils
from placebot.core.data_dirs import get_output_dir


def _dataset_info(tsv_dataset):
    return {
        "filename": tsv_dataset.name,
        "filepath": str(tsv_dataset),
        "row_count": 2,
    }


def test_resume_state_written_under_user_output_dir(
    isolated_home, tsv_dataset, tmp_path, monkeypatch
):
    # Run from a directory with no writable ``output/`` subfolder.
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    dataset_info = _dataset_info(tsv_dataset)
    resume_utils.update_resume_state(
        dataset_info, last_completed_index=0, stats={}, model_name="Test Model"
    )

    expected = os.path.join(
        str(get_output_dir()), f"{tsv_dataset.stem}_resume.json"
    )
    assert os.path.exists(expected)
    # No stray relative ``output/`` directory should be created in the CWD.
    assert not (workdir / "output").exists()


def test_resume_roundtrip_and_cleanup(isolated_home, tsv_dataset):
    dataset_info = _dataset_info(tsv_dataset)

    resume_utils.update_resume_state(
        dataset_info, last_completed_index=0, stats={"api_calls_made": 3},
        model_name="Test Model",
    )

    info = resume_utils.check_for_resume(dataset_info)
    assert info is not None
    assert info["completed"] == 1
    assert info["remaining"] == 1

    resume_utils.cleanup_resume_state(dataset_info)
    assert resume_utils.check_for_resume(dataset_info) is None
