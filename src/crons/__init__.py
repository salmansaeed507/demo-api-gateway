from fastapi import FastAPI

from ._scheduler import crons

def init(app: FastAPI) -> None:
    """Bind the cron scheduler to the FastAPI app lifespan."""
    crons.init_app(app)
