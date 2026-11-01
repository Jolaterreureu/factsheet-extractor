import json
import sys
from pathlib import Path

from pydantic import ValidationError

from factsheet.schema import Factsheet

folder = sys.argv[1] if len(sys.argv) > 1 else "ground_truth"
files = sorted(Path(folder).glob("*.json"))
done = 0
todo = []
for path in files:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"{path.name}: not valid JSON ({e})")
        continue
    if data.get("fund_name") is None and data.get("as_of_date") is None:
        todo.append(path.stem)
        continue
    try:
        Factsheet.model_validate_json(path.read_text(), strict=True)
    except ValidationError as e:
        print(f"{path.name}: {e.error_count()} error(s)")
        for err in e.errors():
            print(f"    {'.'.join(map(str, err['loc']))}: {err['msg']}")
        continue
    empty = [k for k, v in data.items() if v is None]
    print(f"{path.name}: ok ({len(empty)} null fields)")
    done += 1

print(f"\nnot started: {len(todo)}")
print(f"{done}/{len(files)} files valid")
