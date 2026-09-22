from fastapi import FastAPI

from ._scheduler import crons

from . import purge_inactive_sessions as purge_inactive_sessions 

def init(app: FastAPI) -> None:
    """Bind the cron scheduler to the FastAPI app lifespan."""
    crons.init_app(app)
