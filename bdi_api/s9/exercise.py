from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

s9 = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Something is wrong with the request"},
    },
    prefix="/api/s9",
    tags=["s9"],
)


class PipelineRun(BaseModel):
    id: str
    repository: str
    branch: str
    status: str
    triggered_by: str
    started_at: datetime
    finished_at: datetime | None
    stages: list[str]


class PipelineStage(BaseModel):
    name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    logs_url: str


# In-memory example data source
PIPELINE_DATA: list[dict] = [
    {
        "id": "run-001",
        "repository": "bts-bdp-assignment",
        "branch": "main",
        "status": "success",
        "triggered_by": "push",
        "started_at": datetime.fromisoformat("2026-03-10T10:00:00"),
        "finished_at": datetime.fromisoformat("2026-03-10T10:05:30"),
        "stages": ["lint", "test", "build"],
    },
    {
        "id": "run-002",
        "repository": "bts-bdp-assignment",
        "branch": "dev",
        "status": "failure",
        "triggered_by": "pull_request",
        "started_at": datetime.fromisoformat("2026-03-11T09:30:00"),
        "finished_at": datetime.fromisoformat("2026-03-11T09:45:00"),
        "stages": ["lint", "test", "build"],
    },
]

STAGE_DATA: dict[str, list[dict]] = {
    "run-001": [
        {
            "name": "lint",
            "status": "success",
            "started_at": datetime.fromisoformat("2026-03-10T10:00:00"),
            "finished_at": datetime.fromisoformat("2026-03-10T10:00:45"),
            "logs_url": "/api/s9/pipelines/run-001/stages/lint/logs",
        },
        {
            "name": "test",
            "status": "success",
            "started_at": datetime.fromisoformat("2026-03-10T10:00:45"),
            "finished_at": datetime.fromisoformat("2026-03-10T10:03:20"),
            "logs_url": "/api/s9/pipelines/run-001/stages/test/logs",
        },
        {
            "name": "build",
            "status": "success",
            "started_at": datetime.fromisoformat("2026-03-10T10:03:20"),
            "finished_at": datetime.fromisoformat("2026-03-10T10:05:30"),
            "logs_url": "/api/s9/pipelines/run-001/stages/build/logs",
        },
    ],
    "run-002": [
        {
            "name": "lint",
            "status": "success",
            "started_at": datetime.fromisoformat("2026-03-11T09:30:00"),
            "finished_at": datetime.fromisoformat("2026-03-11T09:32:00"),
            "logs_url": "/api/s9/pipelines/run-002/stages/lint/logs",
        },
        {
            "name": "test",
            "status": "failure",
            "started_at": datetime.fromisoformat("2026-03-11T09:32:00"),
            "finished_at": datetime.fromisoformat("2026-03-11T09:45:00"),
            "logs_url": "/api/s9/pipelines/run-002/stages/test/logs",
        },
        {
            "name": "build",
            "status": "skipped",
            # Pydantic requires datetime, so we use started_at = finished_at = pipeline started_at
            "started_at": PIPELINE_DATA[1]["started_at"],
            "finished_at": PIPELINE_DATA[1]["started_at"],
            "logs_url": "/api/s9/pipelines/run-002/stages/build/logs",
        },
    ],
}


@s9.get("/pipelines")
def list_pipelines(
    repository: str | None = None,
    status_filter: str | None = None,
    num_results: int = 100,
    page: int = 0,
) -> list[PipelineRun]:
    """List CI/CD pipeline runs with their status.

    Returns a list of pipeline runs, optionally filtered by repository and status.
    Ordered by started_at descending (most recent first).
    Paginated with `num_results` per page and `page` number (0-indexed).

    Valid statuses: "success", "failure", "running", "pending"
    Valid triggered_by values: "push", "pull_request", "schedule", "manual"
    """
    # TODO: Return pipeline runs from your data source
    pipelines = [PipelineRun(**p) for p in PIPELINE_DATA]

    # TODO: Filter by repository if provided
    if repository:
        pipelines = [p for p in pipelines if p.repository == repository]

    # TODO: Filter by status if status_filter is provided
    if status_filter:
        pipelines = [p for p in pipelines if p.status == status_filter]

    # TODO: Order by started_at descending
    pipelines.sort(key=lambda p: p.started_at, reverse=True)

    # TODO: Apply pagination
    start = page * num_results
    end = start + num_results
    return pipelines[start:end]


@s9.get("/pipelines/{pipeline_id}/stages")
def get_pipeline_stages(pipeline_id: str) -> list[PipelineStage]:
    """Get the stages of a specific pipeline run.

    Returns the stages in execution order.
    Each stage has a name, status, timestamps, and a logs URL.

    Typical stages: "lint", "test", "build", "deploy"
    """
    # TODO: Look up the pipeline run by pipeline_id
    stages = STAGE_DATA.get(pipeline_id)

    # TODO: Return 404 if pipeline_id not found
    if stages is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # TODO: Return the stages with their details
    return [PipelineStage(**s) for s in stages]

