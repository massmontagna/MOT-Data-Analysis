"""Download and unzip the 2024 DVSA anonymised MOT data into data/raw/.

    python src/download_data.py              # everything (2.2 GB of zips, 12.8 GB unzipped)
    python src/download_data.py --only lookup

URLs are the ones listed for "Anonymised MOT tests and results" on data.gov.uk
(CKAN id anonymised-mot-tests-and-results). Files already unzipped are skipped.
"""
import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://edh-dvsa-data-gov-uk-files-prod.s3.eu-west-1.amazonaws.com/"

# name -> (url, folder it must end up in under data/raw; None = a single file, not a zip)
FILES = {
    "results": (BASE + "MOT+testing+data+results+(2024).zip", "MOT testing data results (2024)"),
    "items": (BASE + "MOT+Testing+data+failure+item+(2024).zip", "MOT Testing data failure item (2024)"),
    "lookup": (BASE + "lookup.zip", "lookup"),
    "guide": (BASE + "mot-testing-data-user-guide-v5.1.odt", None),
}

# The lookup.zip published in Nov 2026 uses shorter names (and pipes) than the copy this project was
# built with, and lacks 36 retired defect codes (data dictionary section 6). Rename to what load_db.py expects.
LOOKUP_RENAMES = {
    "item_detail.csv": "dft_item_detail_extract.csv",
    "item_group.csv": "dft_item_group_extract.csv",
    "mdr_fuel_types.csv": "dft_mdr_fuel_type_extract.csv",
    "mdr_rfr_location.csv": "dft_mdr_rfr_location_extract.csv",
    "mdr_test_outcome.csv": "dft_mdr_test_outcome_extract.csv",
    "mdr_test_type.csv": "dft_mdr_test_type_extract.csv",
}


def download(url, dest):
    print(f"downloading {url}", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    tmp.rename(dest)  # only a complete download gets the real name


def unzip(zip_path, target):
    """Unzip into target, so the CSVs end up directly in it even if the zip has its own top folder."""
    tmp = target.with_name(target.name + ".unzipping")
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(tmp)  # zipfile strips absolute paths and '..' itself
    inner = [p for p in tmp.iterdir() if p.name != "__MACOSX"]
    src = inner[0] if len(inner) == 1 and inner[0].is_dir() else tmp
    src.rename(target)
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", default=ROOT / "data" / "raw", type=Path)
    parser.add_argument("--only", choices=FILES, action="append", help="download just these (repeatable)")
    args = parser.parse_args()
    args.raw.mkdir(parents=True, exist_ok=True)

    for name in args.only or FILES:
        url, folder = FILES[name]
        file_name = urllib.request.unquote(url.rsplit("/", 1)[1]).replace("+", " ")
        dest = args.raw / file_name
        if folder is None:
            if not dest.exists():
                download(url, dest)
            continue
        target = args.raw / folder
        if target.exists():
            print(f"{target} already exists, skipping")
            continue
        if not dest.exists():
            download(url, dest)
        unzip(dest, target)
        dest.unlink()
        if name == "lookup":
            for old, new in LOOKUP_RENAMES.items():
                if (target / old).exists():
                    (target / old).rename(target / new)
        print(f"unzipped into {target}")


if __name__ == "__main__":
    main()
