"""CLI de validación de fuentes."""

from __future__ import annotations

import argparse
import json

from inventory_forecasting.data.landing import stage_sources, validate_sources


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="store-sales-time-series-forecasting")
    parser.add_argument("--landing-dir", default="data/landing")
    parser.add_argument("--stage", action="store_true")
    args = parser.parse_args()
    if args.stage:
        result = stage_sources(args.input_dir, args.landing_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    results = [result.as_dict() for result in validate_sources(args.input_dir)]
    print(json.dumps(results, indent=2, ensure_ascii=False))
    if any(not result["valid"] for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

