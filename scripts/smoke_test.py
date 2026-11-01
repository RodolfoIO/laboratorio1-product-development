"""Smoke test pequeño para validar el flujo completo sin entrenar todo Kaggle."""

from pathlib import Path
import tempfile

from inventory_forecasting.models.train import train_and_evaluate
from inventory_forecasting.product.forecast import publish_forecast
from inventory_forecasting.product.monitor import monitor_forecasts


def main() -> None:
    source = Path("store-sales-time-series-forecasting")
    if not source.exists():
        raise SystemExit("No existe la carpeta de datos de Kaggle")
    with tempfile.TemporaryDirectory(prefix="lab1-smoke-") as tmp:
        root = Path(tmp)
        # Usa un subconjunto reproducible del dataset completo.
        import pandas as pd

        subset = root / "sources"
        subset.mkdir()
        train = pd.read_csv(source / "train.csv", parse_dates=["date"])
        # Cuatro series y 70 días: suficiente para validar el flujo completo
        # sin convertir el smoke test en un entrenamiento de producción.
        train = train[
            (train["date"] <= train["date"].min() + pd.Timedelta(70, unit="D"))
            & (train["store_nbr"] <= 2)
            & (train["family"].isin(sorted(train["family"].unique())[:2]))
        ]
        train.to_csv(subset / "train.csv", index=False)
        for name in ["stores.csv", "holidays_events.csv", "oil.csv", "transactions.csv"]:
            pd.read_csv(source / name).to_csv(subset / name, index=False)
        result = train_and_evaluate(subset, root / "models", "params.yaml", "configs/business.yaml")
        publish_forecast(subset, str(train["date"].max().date()), root / "forecasts", root / "models" / "global_model.joblib")
        report = monitor_forecasts(subset, root / "forecasts", root / "reports", "configs/business.yaml")
        print({"selected_model": result["selected_model"], "published": report["published_rows"], "pending": report["pending_rows"]})


if __name__ == "__main__":
    main()
