import pytest

from n2o.signal.dataset import (
    DATASET_LIBRARY,
    DatasetInfo,
    DatasetLoader,
    write_metadata_template,
)


def test_list_libraries_returns_sorted_registered_names():
    assert DatasetLoader.list_libraries() == sorted(DATASET_LIBRARY)


def test_list_libraries_includes_ofner2017():
    assert "Ofner2017" in DatasetLoader.list_libraries()


def test_name_mode_accepts_a_listed_library():
    loader = DatasetLoader(name="Ofner2017")
    assert loader.name == "Ofner2017"
    assert loader.path is None


def test_name_mode_rejects_a_library_not_in_the_list():
    with pytest.raises(ValueError, match="unknown dataset library"):
        DatasetLoader(name="NotRegistered")


def test_path_mode_requires_a_metadata_file_to_already_exist(tmp_path):
    with pytest.raises(FileNotFoundError, match="write_metadata_template"):
        DatasetLoader(path=tmp_path)


def test_path_mode_succeeds_once_metadata_exists(tmp_path):
    write_metadata_template(tmp_path)
    loader = DatasetLoader(path=tmp_path)
    assert loader.name is None
    assert loader.path == tmp_path


def test_requires_exactly_one_of_path_or_name():
    with pytest.raises(ValueError):
        DatasetLoader()
    with pytest.raises(ValueError):
        DatasetLoader(path="/data/x", name="Ofner2017")


def test_info_name_mode_returns_dataset_info_for_ofner2017():
    info = DatasetLoader(name="Ofner2017").info()
    assert isinstance(info, DatasetInfo)
    assert "Ofner" in info.source
    assert info.data_range_sec == (0.0, 3.0)
    assert info.num_channels == 61
    assert info.metadata["num_subjects"] == 15


def test_info_path_mode_reads_the_metadata_template(tmp_path):
    write_metadata_template(tmp_path)
    info = DatasetLoader(path=tmp_path).info()
    assert info == DatasetInfo()


def test_library_tree_refuses_to_print_inline_past_the_limit():
    with pytest.raises(ValueError, match="inline_limit"):
        DatasetLoader.library_tree(inline_limit=1)


def test_library_tree_writes_to_file_when_requested(tmp_path):
    target = tmp_path / "library.md"
    message = DatasetLoader.library_tree(to_file=target)
    assert target.exists()
    assert "moabb" in target.read_text()
    assert str(target) in message
