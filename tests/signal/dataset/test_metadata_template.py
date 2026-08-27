import pytest

from n2o.signal.dataset import DatasetInfo, metadata_template


def test_write_template_creates_a_loadable_blank_dataset_info(tmp_path):
    target = metadata_template.write_template(tmp_path)
    assert target == tmp_path / "dataset_info.py"
    info = metadata_template.load(tmp_path)
    assert info == DatasetInfo()


def test_write_template_creates_missing_parent_folders(tmp_path):
    folder = tmp_path / "nested" / "recording"
    metadata_template.write_template(folder)
    assert (folder / "dataset_info.py").exists()


def test_write_template_refuses_to_overwrite_an_existing_file(tmp_path):
    metadata_template.write_template(tmp_path)
    with pytest.raises(FileExistsError):
        metadata_template.write_template(tmp_path)


def test_load_without_a_template_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="write_template"):
        metadata_template.load(tmp_path)


def test_load_reflects_user_edits(tmp_path):
    metadata_template.write_template(tmp_path)
    target = tmp_path / "dataset_info.py"
    target.write_text(
        target.read_text().replace(
            "source=None,", 'source="My Lab EMG recording (2026)",'
        )
    )
    info = metadata_template.load(tmp_path)
    assert info.source == "My Lab EMG recording (2026)"
