import os
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PATH = Path(os.getenv("APPDATA")) / "StardewValley"
SAVE_PATH = PATH / "Saves"
if not SAVE_PATH.exists():
    exit()
BU_PATH = PATH / "Backup"
SEASONS = {"spring": "1", "summer": "2", "fall": "3", "winter": "4"}


def game_date(save_file: Path) -> str:
    root = ET.parse(save_file).getroot()
    year = int(root.find("year").text)
    season = root.find("currentSeason").text
    day = int(root.find("dayOfMonth").text)
    return f"{year:02d}-{SEASONS[season]}-{day:02d}"


def save(slot_name: str) -> None:
    save_dir = next((d for d in SAVE_PATH.glob(f"{slot_name}_*") if d.is_dir()), None)
    if save_dir is None:
        raise ValueError(f"Could not backup slot named {slot_name}.")
    slot_name = save_dir.name
    bu_dir = BU_PATH / slot_name
    bu_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{date.today().isoformat()} {game_date(save_dir / slot_name)}.zip"
    zip_path = bu_dir / file_name
    zip_path.touch()
    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as zf:
        zf.write(save_dir / slot_name, slot_name)
        zf.write(save_dir / "SaveGameInfo", "SaveGameInfo")
    print(f"Successfully backed up {file_name} for slot {slot_name}.")


def restore(slot_name: str, file_name: str | None = None) -> None:
    bu_dir = next((d for d in BU_PATH.glob(f"{slot_name}_*") if d.is_dir()), None)
    if bu_dir is None:
        raise ValueError(f"Could not find a backup for slot {slot_name}.")
    saves = bu_dir.glob("*.zip")
    if file_name is None:
        _restore(sorted(saves)[0])
    elif file_name in [s.name for s in saves]:
        _restore(bu_dir / file_name)


def _restore(archive: Path) -> None:
    slot_name = archive.parent.name
    save_dir = SAVE_PATH / slot_name
    with ZipFile(archive, mode="r") as zf:
        zf.extractall(path=save_dir)
    print(f"Successfully restored backup {archive.stem} for slot {slot_name}.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="StardewSaveManager")
    parser.add_argument("mode", choices=["s", "r"], help="Save or Restore slot.")
    parser.add_argument("-s", "--slot", help="Name of the save slot (farm).")
    parser.add_argument("-f", "--file_name", help="Specific backup file to restore.")

    args = parser.parse_args()

    if args.mode.lower() in ["s", "save"]:
        if args.slot is not None:
            save(args.slot)
        else:
            for d in SAVE_PATH.iterdir():
                if d.is_dir():
                    save(d.name.split("_")[0])

    elif args.mode.lower() in ["r", "restore"]:
        if args.slot is None:
            raise ValueError("Must specify a slot to restore!")
        restore(args.slot, args.file_name)
