import os

import mlflow

from screening.config import PROJECT_ROOT


def setup_mlflow(cfg: dict) -> None:
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    uri = cfg["mlflow"]["tracking_uri"]
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        # keep the DB in the project root no matter where the command is run from
        uri = "sqlite:///" + (PROJECT_ROOT / uri.removeprefix("sqlite:///")).as_posix()
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(cfg["mlflow"]["experiment"])


def log_df(df, name: str) -> None:
    """Log a DataFrame as a CSV artifact."""
    mlflow.log_text(df.to_csv(index=False), f"{name}.csv")
