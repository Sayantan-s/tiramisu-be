from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import create_db_and_tables
from app.routers import auth, dev, events, expenses, groups, invites, me, settlements


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="tiramisu-be", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(groups.router)
app.include_router(invites.router)
app.include_router(expenses.router)
app.include_router(settlements.router)
app.include_router(events.router)
app.include_router(dev.router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
