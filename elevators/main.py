from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import create_engine, Column, Boolean, Integer, DateTime, literal
from sqlalchemy.orm import declarative_base, sessionmaker, Session


DATABASE_URL = "sqlite:///./elevators.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI()

#Models to be stored in the database

class State(Base):
    """
    The State class represents a snapshot of the elevator's status.
    Attributes:
        id (int): The unique identifier for the state record.
        current_floor (int): The current floor where the elevator is based.
        state_time (datetime): The time when the state was recorded.
        vacant (bool): Indicates if the elevator is vacant.
        mooving (bool): Indicates if the elevator is moving.
    """
    __tablename__ = "states"
    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    current_floor = Column(Integer, nullable=False)
    state_time = Column(DateTime, default=datetime.utcnow)
    vacant = Column(Boolean,  nullable=False)
    mooving = Column(Boolean,  nullable=False)
    
class Demand(Base):
    """
    The Demand class represents a demand made for the elevator.
    Attributes:
        id (int): The unique identifier for the demand record.
        demand_floor (int): The floor from which the demand is made.
        demand_time (datetime): The time when the demand was recorded.
    """
    __tablename__ = "demands"
    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    demand_floor = Column(Integer, nullable=False)
    demand_time = Column(DateTime, default=datetime.utcnow)

    

#Pydantic Schemas

class StateBase(BaseModel):
    current_floor: int
    state_time: datetime
    vacant: bool
    mooving: bool

class DemandBase(BaseModel):
    demand_floor : int
    demand_time : datetime


#Dependency or Data Base Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


#Endpoints
@app.get("/state", summary = 'Get all elevator states', description = 'Get all situations related to the elavator')
def read_states(db: Session = Depends(get_db)):
    """
    Retrieve all state records.
    Args:
        db (Session): The database session dependency.
    Returns:
        List[State]: A list of all state records.
    """
    
    states = db.query(State).all()
    return states

@app.post("/state", summary = 'Log a new elevator state', 
          description = 'Crate a situation of the elevator, whether it is moving, vacant, current floor and time', status_code=201)
def create_state(state: StateBase, db: Session = Depends(get_db)):
    """
    Log a new state record.
    Args:
        state (StateBase): The state data to be logged.
        db (Session): The database session dependency.
    Returns:
        State: The newly created state record.
    """
    new_state = State(
        current_floor=state.current_floor,
        vacant=state.vacant,
        mooving=state.mooving,
        state_time=state.state_time
    )
    db.add(new_state)
    db.commit()
    db.refresh(new_state)
    return new_state


@app.get("/demand", summary = 'Get all elevator demands', description = 'Get all demands related to the elavator')
def read_demands(db: Session = Depends(get_db)):
    """
    Retrieve all demand records.
    Args:
        db (Session): The database session dependency. 
    Returns:
        List[Demand]: A list of all demand records.
    """
    demands = db.query(Demand).all()
    return demands

@app.post("/demand", summary = 'Log a new elevator demand', 
          description = 'Crate a new demand for the elevator', status_code=201)

def create_demand(demand: DemandBase, db: Session = Depends(get_db)):
    """
    Log a new demand record and automatically generate a new state.
    Args:
        demand (DemandBase): The demand data to be logged.
        db (Session): The database session dependency.
        
    Returns:
        Demand: The newly created demand record.
    """
    
    # Log the demand.
    new_demand = Demand(
        demand_floor= demand.demand_floor,
        demand_time= demand.demand_time 
    )
    db.add(new_demand)
    db.commit()
    db.refresh(new_demand)
    
    return new_demand

@app.get("/dataset", summary='Get dataset for model training', description='Returns a dataset for training the prediction model')
def get_dataset(db: Session = Depends(get_db)):
    """
    Retrieve a dataset suitable for training a prediction model.
    Args:
        db (Session): The database session dependency.     
    Returns:
        List[dict]: A list of records where each record contains:
            - event_type_is_resting (bool): True if the event is a resting state, False if it is a demand.
            - floor (int): The elevator floor associated with the event.
            - time (datetime): The timestamp of the event.
    """
    # Query resting states as events
    resting_query = db.query(
        literal(True).label("event_type_is_resting"),
        State.current_floor.label("floor"),
        State.state_time.label("time")
    ).filter(
        State.vacant == True,
        State.mooving == False
    )
    
    # Query demand events
    demand_query = db.query(
        literal(False).label("event_type_is_resting"),
        Demand.demand_floor.label("floor"),
        Demand.demand_time.label("time")
    )
    
    # Combine the queries using union_all and order by the event time.
    union_query = resting_query.union_all(demand_query).order_by("time")
    
    results = union_query.all()
    
    # Convert SQLAlchemy row objects to dictionaries.
    dataset = [{"event_type_is_resting": row.event_type_is_resting, "floor": row.floor, "time": row.time} for row in results]
    return dataset