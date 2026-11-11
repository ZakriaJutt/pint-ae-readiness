"""B2 storage through the S3 API against local MinIO: uploads and generated files land under
the firm's prefix, the worker reads them back, a generated file downloads only for its own
firm through GET /files/{id}, objects are not publicly readable, and test objects are removed.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from pintae_api.main import create_app
from pintae_core.config import get_settings
from pintae_core.storage import S3ObjectStore
from tests.integration import flow
from tests.integration.conftest import Env, Firm


def _store() -> S3ObjectStore:
    cfg = get_settings()
    if not (cfg.s3_access_key_id and cfg.s3_secret_access_key):
        pytest.skip("PINTAE_S3_* credentials are not set (backend/.env)")
    store = S3ObjectStore(
        cfg.s3_bucket,
        endpoint_url=cfg.s3_endpoint_url or "http://127.0.0.1:9000",
        region=cfg.s3_region,
        access_key_id=cfg.s3_access_key_id,
        secret_access_key=cfg.s3_secret_access_key,
    )
    if not store.writable():
        pytest.skip("MinIO bucket is not reachable")
    return store


@pytest.fixture
def s3_env(
    admin_engine: Engine, app_engine: Engine, publisher_id: uuid.UUID, tmp_path: Path
) -> Iterator[Env]:
    store = _store()
    clock = [datetime.now(tz=UTC)]
    app = create_app(engine=app_engine, store=store, clock=lambda: clock[0])
    with TestClient(app, base_url="https://testserver") as client:
        e = Env(admin_engine, app_engine, client, store, publisher_id, clock)
        firms: list[uuid.UUID] = []
        orig = e.firm

        def firm(name: str = "Synthetic Bookkeeping FZ-LLC") -> Firm:
            f = orig(name)
            firms.append(f.id)
            return f

        e.firm = firm  # type: ignore[method-assign]
        yield e
        for fid in firms:
            store.delete_prefix(f"firms/{fid}/")


def test_upload_and_generated_file_round_trip_per_firm(s3_env: Env) -> None:
    env = s3_env
    store = env.store
    assert isinstance(store, S3ObjectStore)
    a, b = env.firm("Firm A"), env.firm("Firm B")
    eid = flow.ready_entity(env, a)  # uploads go to MinIO; the worker parses them from MinIO
    with env.admin.connect() as conn:
        keys = conn.execute(
            text("SELECT dataset, storage_key FROM uploads WHERE firm_id = :f"), {"f": a.id}
        ).all()
    assert len(keys) == 3
    for ds, key in keys:
        assert key.startswith(f"firms/{a.id}/entities/{eid}/source-{ds}/")
        assert store.exists(key)
    r = env.client.post(f"/api/v1/entities/{eid}/findings/exports", headers=a.h("preparer"))
    assert r.status_code == 201, r.text
    fid = r.json()["file_id"]
    with env.admin.connect() as conn:
        fkey = conn.execute(
            text("SELECT storage_key FROM files WHERE id = :i"), {"i": fid}
        ).scalar_one()
    assert fkey.startswith(f"firms/{a.id}/generated/fix_list/") and store.exists(fkey)
    # Download for the owning firm only.
    r = env.client.get(f"/api/v1/files/{fid}", headers=a.h("reviewer"))
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/csv; charset=utf-8"
    assert r.headers["content-disposition"].startswith("attachment;")
    assert r.headers["cache-control"] == "no-store"
    assert r.content.decode("utf-8-sig").startswith('"rule","severity","dataset"')
    assert env.client.get(f"/api/v1/files/{fid}", headers=b.h()).status_code == 404
    assert env.client.get(f"/api/v1/files/{fid}").status_code == 401
    assert env.client.get(f"/api/v1/files/{uuid.uuid4()}", headers=a.h()).status_code == 404
    r = env.client.post(f"/api/v1/entities/{eid}/findings/exports", headers=b.h())
    assert r.status_code == 404
    # No public access to the bucket: an unsigned request is refused by MinIO.
    cfg = get_settings()
    base = (cfg.s3_endpoint_url or "http://127.0.0.1:9000").rstrip("/")
    anon = httpx.get(f"{base}/{cfg.s3_bucket}/{fkey}", timeout=5)
    assert anon.status_code == 403
    listing = httpx.get(f"{base}/{cfg.s3_bucket}?list-type=2", timeout=5)
    assert listing.status_code == 403


def test_test_objects_are_removed(s3_env: Env) -> None:
    store = s3_env.store
    assert isinstance(store, S3ObjectStore)
    f = uuid.uuid4()
    key = f"firms/{f}/generated/export/{uuid.uuid4()}"
    store.put(key, b"synthetic")
    assert store.get(key) == b"synthetic"
    assert store.delete_prefix(f"firms/{f}/") == 1
    assert not store.exists(key)
    with pytest.raises(ValueError):
        store.put("not-a-firm-key", b"x")
