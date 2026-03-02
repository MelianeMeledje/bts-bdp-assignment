from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, status
from fastapi.params import Query

from sqlalchemy import create_engine, text

from bdi_api.settings import Settings

settings = Settings()

s5 = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Something is wrong with the request"},
    },
    prefix="/api/s5",
    tags=["s5"],
)

engine = create_engine(settings.db_url, future=True)

BASE_DIR = Path(__file__).resolve().parents[0]

@s5.post("/db/init")
def init_database() -> str:
    """Create all HR database tables (department, employee, project,
    employee_project, salary_history) with their relationships and indexes.

    Use the BDI_DB_URL environment variable to configure the database connection.
    Default: sqlite:///hr_database.db
    """
    # TODO: Connect to the database using SQLAlchemy or psycopg2
    with engine.begin() as conn:
        # Drop tables
        conn.execute(text("DROP TABLE IF EXISTS salary_history CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS employee_project CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS project CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS employee CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS department CASCADE;"))

        # Load and execute schema 
        schema_path = BASE_DIR / "sql" / "hr_schema.sql"
        schema_sql = schema_path.read_text()

        conn.execute(text(schema_sql))
    return "OK"


@s5.post("/db/seed")
def seed_database() -> str:
    """Populate the HR database with sample data.

    Inserts departments, employees, projects, assignments, and salary history.
    """
    # TODO: Connect to the database
    # TODO: Execute the seed data SQL (see hr_seed_data.sql)
    with engine.begin() as conn:
        seed_path = BASE_DIR / "sql" / "hr_seed_data.sql"
        seed_sql = seed_path.read_text()

        conn.execute(text(seed_sql))

    return "OK"


@s5.get("/departments/")
def list_departments() -> list[dict]:
    """Return all departments.

    Each department should include: id, name, location
    """
    # TODO: Query all departments and return as list of dicts
    query = "SELECT id, name, location FROM department;"

    with engine.connect() as conn:
        result = conn.execute(text(query)).all()
        return [dict(row._mapping) for row in result]


@s5.get("/employees/")
def list_employees(
    page: Annotated[
        int,
        Query(description="Page number (1-indexed)", ge=1),
    ] = 1,
    per_page: Annotated[
        int,
        Query(description="Number of employees per page", ge=1, le=100),
    ] = 10,
) -> list[dict]:
    """Return employees with their department name, paginated.

    Each employee should include: id, first_name, last_name, email, salary, department_name
    """
    # TODO: Query employees with JOIN to department, apply OFFSET and LIMIT
    offset = (page - 1) * per_page

    query = """
        SELECT e.id, e.first_name, e.last_name, e.email, e.salary, d.name AS department_name
        FROM employee e
        JOIN department d ON e.department_id = d.id
        ORDER BY e.id
        LIMIT :limit OFFSET :offset;
    """

    with engine.connect() as conn:
        result = conn.execute(
            text(query),
            {"limit": per_page, "offset": offset},
        ).all()

        return [dict(row._mapping) for row in result]


@s5.get("/departments/{dept_id}/employees")
def list_department_employees(dept_id: int) -> list[dict]:
    """Return all employees in a specific department.

    Each employee should include: id, first_name, last_name, email, salary, hire_date
    """
    # TODO: Query employees filtered by department_id
    query = """
        SELECT id, first_name, last_name, email, salary, hire_date
        FROM employee
        WHERE department_id = :dept_id
        ORDER BY id;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query), {"dept_id": dept_id}).all()
        return [dict(row._mapping) for row in result]


@s5.get("/departments/{dept_id}/stats")
def department_stats(dept_id: int) -> dict:
    """Return KPI statistics for a department.

    Response should include: department_name, employee_count, avg_salary, project_count
    """
    # TODO: Calculate department statistics using JOINs and aggregations
    query = """
        SELECT d.name AS department_name,
               COUNT(DISTINCT e.id) AS employee_count,
               AVG(e.salary) AS avg_salary,
               COUNT(DISTINCT ep.project_id) AS project_count
        FROM department d
        LEFT JOIN employee e ON e.department_id = d.id
        LEFT JOIN employee_project ep ON ep.employee_id = e.id
        WHERE d.id = :dept_id
        GROUP BY d.name;
    """

    with engine.connect() as conn:
        row = conn.execute(text(query), {"dept_id": dept_id}).first()
        return dict(row._mapping) if row else {}


@s5.get("/employees/{emp_id}/salary-history")
def salary_history(emp_id: int) -> list[dict]:
    """Return the salary evolution for an employee, ordered by date.

    Each entry should include: change_date, old_salary, new_salary, reason
    """
    # TODO: Query salary_history for the given employee, ordered by change_date
    query = """
            SELECT change_date, old_salary, new_salary, reason
            FROM salary_history
            WHERE employee_id = :emp_id
            ORDER BY change_date;
        """

    with engine.connect() as conn:
            result = conn.execute(text(query), {"emp_id": emp_id}).all()
            return [dict(row._mapping) for row in result]
