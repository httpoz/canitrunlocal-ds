import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import validate  # noqa: E402

GPU_SCHEMA = json.loads((REPO_ROOT / "schema" / "gpu.schema.json").read_text())


def test_validate_schema_accepts_valid_entry():
    entries_by_file = {
        "nvidia.json": [
            {
                "id": "nvidia-rtx-4070",
                "name": "GeForce RTX 4070",
                "manufacturer": "NVIDIA",
                "vramGb": 12,
                "memoryBandwidthGbps": 504.2,
            }
        ]
    }
    errors = validate.validate_schema(entries_by_file, GPU_SCHEMA)
    assert errors == []


def test_validate_schema_rejects_missing_required_field():
    entries_by_file = {
        "nvidia.json": [
            {
                "id": "nvidia-rtx-4070",
                "name": "GeForce RTX 4070",
                "manufacturer": "NVIDIA",
                "vramGb": 12,
            }
        ]
    }
    errors = validate.validate_schema(entries_by_file, GPU_SCHEMA)
    assert len(errors) == 1
    assert "nvidia.json[0]" in errors[0]


def test_validate_schema_rejects_unknown_manufacturer():
    entries_by_file = {
        "nvidia.json": [
            {
                "id": "nvidia-rtx-4070",
                "name": "GeForce RTX 4070",
                "manufacturer": "Nvidia Corp",
                "vramGb": 12,
                "memoryBandwidthGbps": 504.2,
            }
        ]
    }
    errors = validate.validate_schema(entries_by_file, GPU_SCHEMA)
    assert len(errors) == 1


def test_check_vendor_consistency_flags_mismatch():
    entries_by_file = {
        "nvidia.json": [
            {"id": "amd-rx-7900xtx", "name": "Radeon RX 7900 XTX", "manufacturer": "AMD"}
        ]
    }
    errors = validate.check_vendor_consistency(entries_by_file)
    assert len(errors) == 1
    assert "nvidia.json[0]" in errors[0]


def test_check_vendor_consistency_passes_matching_manufacturer():
    entries_by_file = {
        "nvidia.json": [
            {"id": "nvidia-rtx-4070", "name": "GeForce RTX 4070", "manufacturer": "NVIDIA"}
        ]
    }
    errors = validate.check_vendor_consistency(entries_by_file)
    assert errors == []


def test_check_duplicates_flags_duplicate_id():
    all_entries = [
        ("gpus/nvidia.json", {"id": "dup-id", "manufacturer": "NVIDIA", "name": "A"}),
        ("gpus/amd.json", {"id": "dup-id", "manufacturer": "AMD", "name": "B"}),
    ]
    errors = validate.check_duplicates(all_entries)
    assert any("duplicate id 'dup-id'" in e for e in errors)


def test_check_duplicates_flags_duplicate_manufacturer_name_pair():
    all_entries = [
        ("gpus/nvidia.json", {"id": "id-1", "manufacturer": "NVIDIA", "name": "GeForce RTX 4070"}),
        ("gpus/nvidia.json", {"id": "id-2", "manufacturer": "NVIDIA", "name": "GeForce RTX 4070"}),
    ]
    errors = validate.check_duplicates(all_entries)
    assert any("GeForce RTX 4070" in e for e in errors)


def test_validate_schema_rejects_invalid_release_date():
    entries_by_file = {
        "nvidia.json": [
            {
                "id": "nvidia-rtx-4070",
                "name": "GeForce RTX 4070",
                "manufacturer": "NVIDIA",
                "vramGb": 12,
                "memoryBandwidthGbps": 504.2,
                "releaseDate": "not-a-date",
            }
        ]
    }
    errors = validate.validate_schema(entries_by_file, GPU_SCHEMA)
    assert len(errors) == 1
    assert "nvidia.json[0]" in errors[0]


def test_check_vendor_consistency_skips_non_string_manufacturer():
    entries_by_file = {
        "nvidia.json": [
            {"id": "nvidia-rtx-4070", "name": "GeForce RTX 4070", "manufacturer": 5}
        ]
    }
    errors = validate.check_vendor_consistency(entries_by_file)
    assert errors == []


def test_load_category_files_rejects_non_list_top_level_json(tmp_path):
    category_dir = tmp_path / "gpus"
    category_dir.mkdir()
    (category_dir / "nvidia.json").write_text(
        json.dumps({"id": "nvidia-rtx-4070", "name": "GeForce RTX 4070", "manufacturer": "NVIDIA"})
    )
    try:
        validate.load_category_files(category_dir)
        assert False, "expected InvalidVendorFileError"
    except validate.InvalidVendorFileError as e:
        assert "nvidia.json" in str(e)


def test_validate_schema_accepts_apple_unified_memory_entry():
    entries_by_file = {
        "apple.json": [
            {
                "id": "apple-m4-pro-24gb",
                "name": "Apple M4 Pro 24GB",
                "manufacturer": "Apple",
                "vramGb": 24,
                "memoryBandwidthGbps": 273,
                "releaseDate": "2024-10-30",
            }
        ]
    }
    errors = validate.validate_schema(entries_by_file, GPU_SCHEMA)
    assert errors == []


def test_check_vendor_consistency_passes_apple_under_gpus():
    entries_by_file = {
        "apple.json": [
            {"id": "apple-m4-pro-24gb", "name": "Apple M4 Pro 24GB", "manufacturer": "Apple"}
        ]
    }
    errors = validate.check_vendor_consistency(entries_by_file)
    assert errors == []


def test_check_duplicates_allows_similar_but_distinct_names():
    all_entries = [
        ("gpus/nvidia.json", {"id": "nvidia-rtx-4070", "manufacturer": "NVIDIA", "name": "GeForce RTX 4070"}),
        ("gpus/nvidia.json", {"id": "nvidia-rtx-4070-ti", "manufacturer": "NVIDIA", "name": "GeForce RTX 4070 Ti"}),
    ]
    errors = validate.check_duplicates(all_entries)
    assert errors == []
