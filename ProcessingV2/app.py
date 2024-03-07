# Standard library imports
import datetime
import logging
import logging.config

# Related third-party imports
import colorlog
from apscheduler.schedulers.background import BackgroundScheduler
from flask import jsonify
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import uvicorn
import yaml

# Local application/library-specific imports
import connexion
from base import Base
from stats import Stats 

# [IMPORT] Enhance logger to include color with colorlog
color_handler = colorlog.StreamHandler()
color_handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s: %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))

# Load configurations and set up logging
with open('./app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())
with open('./log_conf.yaml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)


# Set up the database engine and session
engine = create_engine(f"sqlite:///{app_config['datastore']['filename']}", echo=True)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

# Get the logger
logger = logging.getLogger('basicLogger')
logger.addHandler(color_handler)

def populate_stats():

    # Get the current datetime in UTC
    current_datetime = datetime.datetime.now(datetime.timezone.utc)
    logger.info("\nStarting to populate stats")

    # Open a new database session
    session = DBSession()
    try:
        # Attempt to retrieve the last statistic entry
        last_stat = session.query(Stats).order_by(Stats.last_updated.desc()).first()
        if last_stat is None:  # Use 'is None' for None checks
            # If no entries exist, explicitly log this and proceed to create a new entry
            logger.info("No stats entries found. Creating a new entry with default values.")
            raise SQLAlchemyError("No stats entries found.")  # Simulate a database error for demonstration

    except SQLAlchemyError as e:
        logger.error(f"Error encountered: {e}")
        # Regardless of the specific error, create a new entry with default values
        current_datetime = datetime.datetime.now(datetime.timezone.utc)  # Ensure this is correct based on your datetime import
        last_stat = Stats(
            num_vehicle_status_events=0,
            num_incident_events=0,
            max_distance_travelled=0,
            max_incident_severity=0,
            last_updated=current_datetime
        )
        session.add(last_stat)
        session.commit()
        logger.info("A new stats entry with initial values has been created.")

    finally:
        session.close()

    # Format the timestamps for the fetch requests
    print(last_stat.last_updated)
    start_timestamp = last_stat.last_updated.strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info(start_timestamp)
    end_timestamp = current_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


    # Fetch new events
    response_vehicle = requests.get(
        f"{app_config['eventstore']['url']}/events/vehicle-status",
        params={'start_timestamp': start_timestamp, 'end_timestamp': end_timestamp},
        headers={'Content-Type': 'application/json'}
    )
    logger.info(response_vehicle)
    vehicle_events = response_vehicle.json() if response_vehicle.status_code == 200 else     logger.info("WARNING")
    

    response_incident = requests.get(
        f"{app_config['eventstore']['url']}/events/incident-report",
        params={'start_timestamp': start_timestamp, 'end_timestamp': end_timestamp},
        headers={'Content-Type': 'application/json'}
    )
    logger.info(response_incident)
    incident_events = response_incident.json() if response_incident.status_code == 200 else     logger.info("WARNING")


    # Log the number of events received and processed
    logger.info(f"Processed {len(vehicle_events)} vehicle events and {len(incident_events)} incident events")


    # Open a new session to commit updates to the database
    session = DBSession()
    
    # Fetch the latest stats record or create a new one if none exists
    latest_stats = session.query(Stats).order_by(Stats.last_updated.desc()).first()


    # Update the fetched or new stats record
    latest_stats.num_vehicle_status_events += len(vehicle_events)
    latest_stats.num_incident_events += len(incident_events)
    # Assuming vehicle_events and incident_events are lists of dictionaries
    # Process vehicle events to find the max distance travelled
    max_distance_travelled = 0
    max_on_time_score = 0

    for event in vehicle_events:
        logger.info(event.get('trace_id'))
        distance = event.get('distanceTravelled', 0)
        on_time_score = event.get('onTimeScore', 0)
        max_distance_travelled = max(max_distance_travelled, distance)
        max_on_time_score = max(max_on_time_score, on_time_score)
    
    # Update the stats object

    new_Stat = Stats(
        num_vehicle_status_events=(latest_stats.num_vehicle_status_events),
        num_incident_events=(latest_stats.num_incident_events),
        max_distance_travelled=max_distance_travelled,
        max_incident_severity=max_on_time_score,  # Assuming incident severity is analogous to on_time_score
        last_updated=current_datetime)

    # Save updates
    session.add(new_Stat)
    session.commit()
    logger.info("Stats updated successfully.\n")
    session.close()


def get_stats():
    logger.info("GET request for stats started")
    
    session = DBSession()
    latest_stat = session.query(Stats).order_by(Stats.last_updated.desc()).first()
    session.close()

    if not latest_stat:
        logger.error("Statistics do not exist")
        # Return a JSON response indicating that statistics do not exist
        return jsonify({"error": "Statistics do not exist"}), 404
    
    logger.info("Retrieving latest entry")
    
    try:
        stats_dict = latest_stat.to_dict()
        logger.debug(f"Stats returned: {stats_dict}")
    except Exception as e:
        logger.error(f"Error processing stats: {e}")
        return jsonify({"error": "Error processing statistics"}), 500

    logger.info("GET request for stats completed")
    return jsonify(stats_dict), 200


# Initialize the scheduler
def init_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(populate_stats, 'interval', seconds=app_config['scheduler']['period_sec'])
    scheduler.start()

# Your Flask app setup and API addition
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api('./Transit.yaml', strict_validation=True, validate_responses=True)

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    init_scheduler()
    # uvicorn.run(app="app:app", host="0.0.0.0", port=8100, log_level="debug", reload=True)
    app.run(port=8100, log_level='debug')
