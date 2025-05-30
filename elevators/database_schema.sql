-- State table
CREATE TABLE states(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    current_floor INTEGER NOT NULL,
    state_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vacant BOOLEAN NOT NULL,
    mooving BOOLEAN NOT NULL
);

-- Demands table
CREATE TABLE demands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demand_floor INTEGER NOT NULL,
    demand_time  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);