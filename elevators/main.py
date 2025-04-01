from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import create_engine, Column, Boolean, Integer, DateTime
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
            - resting_floor (int): The elevator's resting floor from the state record.
            - resting_time (datetime): The time when the elevator was in the resting state.
            - demand_floor (int): The floor requested in the demand.
            - demand_time (datetime): The time when the demand was recorded.
    """
    dataset = []
    # Retrieve all demand records ordered by demand_time
    demands = db.query(Demand).order_by(Demand.demand_time).all()
    for demand in demands:
        # For each demand, find the most recent state record where the elevator was resting.
        resting_state = db.query(State).filter(
            State.state_time <= demand.demand_time,
            State.vacant == True,
            State.mooving == False
        ).order_by(State.state_time.desc()).first()
        if resting_state:
            record = {
                "resting_floor": resting_state.current_floor,
                "resting_time": resting_state.state_time,
                "demand_floor": demand.demand_floor,
                "demand_time": demand.demand_time,
            }
            dataset.append(record)
    return dataset