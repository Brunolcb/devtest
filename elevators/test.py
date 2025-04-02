import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from main import app, Base, get_db

#Use an in-memory SQLite database with StaticPool for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

#Create all tables in the in-memory database
Base.metadata.create_all(bind=engine_test)

#Override the get_db dependency to use the in-memory test database
def override_get_db():
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

#Override the get_db dependency in our app.
app.dependency_overrides[get_db] = override_get_db

#Create a TestClient instance for our app.
client = TestClient(app)

def test_create_and_read_state():
    """
    Test creating a new elevator state and retrieving the list of states.
    
    Steps:
      1. POST a new state record.
      2. GET the state records and verify that the created state is present.
    """
    
    state_payload = {
        "current_floor": 1,
        "state_time": datetime.utcnow().isoformat(),
        "vacant": True,
        "mooving": False
    }
    # Create a new state.
    response = client.post("/state", json=state_payload)
    assert response.status_code == 201, f"Expected status 201, got {response.status_code}"
    created_state = response.json()
    assert created_state["current_floor"] == state_payload["current_floor"]
    assert created_state["vacant"] is True
    assert created_state["mooving"] is False

    # Retrieve all states.
    response = client.get("/state")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    states = response.json()
    assert isinstance(states, list)
    # There should be at least one state (the one we just created).
    assert len(states) > 0

def test_create_and_read_demand():
    """
    Test creating a new elevator demand and retrieving the list of demands.
    
    Steps:
      1. POST a new demand record.
      2. GET the demand records and verify that the created demand is present.
    """
    
    demand_payload = {
        "demand_floor": 3,
        "demand_time": datetime.utcnow().isoformat()
    }
    # Create a new demand.
    response = client.post("/demand", json=demand_payload)
    assert response.status_code == 201, f"Expected status 201, got {response.status_code}"
    created_demand = response.json()
    assert created_demand["demand_floor"] == demand_payload["demand_floor"]

    # Retrieve all demands.
    response = client.get("/demand")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    demands = response.json()
    assert isinstance(demands, list)
    assert len(demands) > 0

def test_get_dataset():
    """
    Test that the /dataset endpoint returns the apropriate data for training the prediction model.
    
    Steps:
      1. POST a resting state record.
      2. POST a demand record.
      3. GET the dataset and verify that:
            - The events are sorted by time.
            - There is at least one resting event and one demand event.
    
    """
    
    # Create a resting state event (simulate a resting event 10 minutes ago).
    resting_state_payload = {
        "current_floor": 2,
        "state_time": (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
        "vacant": True,
        "mooving": False
    }
    response = client.post("/state", json=resting_state_payload)
    assert response.status_code == 201, f"Expected status 201, got {response.status_code}"

    # Create a demand event with a current timestamp.
    demand_payload = {
        "demand_floor": 4,
        "demand_time": datetime.utcnow().isoformat()
    }
    response = client.post("/demand", json=demand_payload)
    assert response.status_code == 201, f"Expected status 201, got {response.status_code}"

    # Retrieve the dataset.
    response = client.get("/dataset")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    dataset = response.json()

    # Verify that the dataset is a list and sorted by time.
    times = [record["time"] for record in dataset]
    sorted_times = sorted(times)
    assert times == sorted_times, "Dataset events are not sorted by time"

    # Verify that there is at least one resting event and one demand event.
    resting_events = [rec for rec in dataset if rec["event_type_is_resting"] is True]
    demand_events = [rec for rec in dataset if rec["event_type_is_resting"] is False]
    assert len(resting_events) > 0, "No resting events found in dataset"
    assert len(demand_events) > 0, "No demand events found in dataset"
