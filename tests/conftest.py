"""
Shared pytest fixtures for the whatspoppingABQ test suite.

IMPORTANT SAFETY NOTE:
database.db_utils.get_connection() calls load_dotenv(override=True) on every
call, which would clobber test env vars with whatever is in a local .env file
(potentially real production credentials). We patch that out below and add a
hard runtime check that refuses to run tests against anything but the test
database. Do not remove the `_verify_test_database` fixture.
"""
import os
import time

import psycopg2
import pytest

TEST_DB_ENV = {
    "DB_HOST": "localhost",
    "DB_PORT": "5433",
    "DB_NAME": "whatspoppingabq_test",
    "DB_USER": "postgres",
    "DB_PASSWORD": "postgres",
}

TABLES_IN_FK_ORDER = [
    # Children before parents, for TRUNCATE ... CASCADE safety regardless of order.
    "app.traffic_measurements",
    "app.events",
    "app.venue_locations",
]


@pytest.fixture(scope="session", autouse=True)
def _test_environment():
    """
    Force test DB env vars for the whole session and prevent db_utils from
    reloading a local .env over them.
    """
    for key, value in TEST_DB_ENV.items():
        os.environ[key] = value

    import database.db_utils as db_utils

    original_load_dotenv = db_utils.load_dotenv
    db_utils.load_dotenv = lambda *args, **kwargs: None
    yield
    db_utils.load_dotenv = original_load_dotenv


@pytest.fixture(scope="session")
def _wait_for_test_db(_test_environment):
    """Block until the docker-compose.test.yml Postgres is accepting connections."""
    last_error = None
    for _ in range(30):
        try:
            conn = psycopg2.connect(
                host=TEST_DB_ENV["DB_HOST"],
                port=TEST_DB_ENV["DB_PORT"],
                dbname=TEST_DB_ENV["DB_NAME"],
                user=TEST_DB_ENV["DB_USER"],
                password=TEST_DB_ENV["DB_PASSWORD"],
                connect_timeout=2,
            )
            conn.close()
            return
        except psycopg2.OperationalError as e:
            last_error = e
            time.sleep(1)
    pytest.exit(
        "Could not reach the test database on localhost:5433.\n"
        "Start it first: docker compose -f docker-compose.test.yml up -d\n"
        f"Last error: {last_error}"
    )


@pytest.fixture(scope="session", autouse=True)
def _verify_test_database(_wait_for_test_db):
    """
    Hard safety guard: every test session must confirm it is talking to the
    test database before any test is allowed to run. This exists specifically
    to prevent tests from ever truncating a real database.
    """
    import database.db_utils as db_utils

    conn = db_utils.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            (actual_db,) = cur.fetchone()
    finally:
        conn.close()

    if actual_db != TEST_DB_ENV["DB_NAME"]:
        pytest.exit(
            f"SAFETY ABORT: connected to database '{actual_db}', expected "
            f"'{TEST_DB_ENV['DB_NAME']}'. Refusing to run tests — this would "
            "risk truncating a real database. Check your DB_* env vars / .env file."
        )


@pytest.fixture(autouse=True)
def clean_db(_verify_test_database):
    """
    Truncate all app tables before every test. db_utils functions open their
    own connections and commit internally, so transaction-rollback isolation
    doesn't work here — truncation between tests is the reliable option.
    """
    import database.db_utils as db_utils

    conn = db_utils.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"TRUNCATE {', '.join(TABLES_IN_FK_ORDER)} RESTART IDENTITY CASCADE"
            )
        conn.commit()
    finally:
        conn.close()
    yield


@pytest.fixture
def db_conn():
    """A raw connection for tests that want to set up data or assert directly."""
    import database.db_utils as db_utils

    conn = db_utils.get_connection()
    yield conn
    conn.close()


@pytest.fixture
def make_venue(db_conn):
    """Factory fixture: insert a venue directly, return its venue_id."""

    def _make_venue(name="Test Venue", lat=35.0844, lng=-106.6504, **overrides):
        fields = {
            "venue_name": name,
            "latitude": lat,
            "longitude": lng,
            **overrides,
        }
        columns = ", ".join(fields.keys())
        placeholders = ", ".join(["%s"] * len(fields))
        with db_conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO app.venue_locations ({columns}) "
                f"VALUES ({placeholders}) RETURNING venue_id",
                list(fields.values()),
            )
            (venue_id,) = cur.fetchone()
        db_conn.commit()
        return venue_id

    return _make_venue