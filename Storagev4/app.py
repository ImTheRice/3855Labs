import connexion
import yaml
import logging.config
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from vehiclestatus import VehicleStatusEvent
from incidentreport import IncidentEvent
from datetime import datetime
import uuid
import colorlog
import json
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread

# [V2.5] Enhance logger to include color with colorlog
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

# [V2] Configuration now externalized to YAML files for improved flexibility
with open('./app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())
with open('./log_conf.yaml', 'r') as f:
    logging.config.dictConfig(yaml.safe_load(f.read()))
    logger = logging.getLogger('basicLogger')
    logger.addHandler(color_handler)


# [V4] KAFKA
logger.info(f"Connecting to MySQL database at {app_config['datastore']['hostname']}:{app_config['datastore']['port']}")
try:
    DB_ENGINE = create_engine(f"mysql+pymysql://{app_config['datastore']['user']}:{app_config['datastore']['password']}@{app_config['datastore']['hostname']}:{app_config['datastore']['port']}/{app_config['datastore']['db']}")
    Session = sessionmaker(bind=DB_ENGINE)
    logger.info("Database engine and sessionmaker successfully created.")
except Exception as e:
    logger.error(f"Failed to create database engine or sessionmaker: {e}")

# [V2] Transitioned to MySQL from SQLite for enhanced scalability and performance.
DB_ENGINE = create_engine(f"mysql+pymysql://{app_config['datastore']['user']}:{app_config['datastore']['password']}@{app_config['datastore']['hostname']}:{app_config['datastore']['port']}/{app_config['datastore']['db']}")
Session = sessionmaker(bind=DB_ENGINE)


# [V2] Added trace id and changed the messages to have color 
def reportVehicleStatusEvent(body):
    session = Session()
    try:
        # Ensure trace_id is provided, generate one if not
        if 'trace_id' not in body or not body['trace_id']:
            body['trace_id'] = str(uuid.uuid4())

        # Remove 'datetime' from the body if present
        body.pop('datetime', None)

        new_event = VehicleStatusEvent(**body)
        session.add(new_event)
        session.commit()
        logger.debug(f"Stored Vehicle Status Event response (Id: {body['trace_id']})")
        return 'Vehicle Status Event logged', 201
    
    except Exception as err:
        logger.error(f"Error storing Vehicle Status Event: {err}")
        session.rollback()
        return f"Error processing Vehicle Status Event: {err}", 500
    
    finally:
        session.close()

def reportIncidentEvent(body):
    session = Session()
    try:
        # Ensure trace_id is provided, generate one if not
        if 'trace_id' not in body or not body['trace_id']:
            body['trace_id'] = str(uuid.uuid4())

        # Remove 'datetime' from the body if present
        body.pop('datetime', None)

        new_event = IncidentEvent(**body)
        session.add(new_event)
        session.commit()
        logger.debug(f"Stored Incident Event response (Id: {body['trace_id']})")
        return 'Incident Event logged', 201
    
    except Exception as err:
        logger.error(f"Error storing Incident Event: {err}")
        session.rollback()
        return f"Error processing Incident Event: {err}", 500
    
    finally:
        session.close()

# [V3] \/
def parse_date(timestamp_str):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):  # Try parsing with and without microseconds
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    raise ValueError("no valid date format found")

def GetreportVehicleStatusEvent(start_timestamp, end_timestamp):
    try:
        start_datetime = parse_date(start_timestamp)
        end_datetime = parse_date(end_timestamp)

        session = Session()
        events = session.query(VehicleStatusEvent).filter(
            VehicleStatusEvent.date_created >= start_datetime,
            VehicleStatusEvent.date_created <= end_datetime
        ).all()
        
        events_list = [event.to_dict() for event in events]
        return events_list, 200
    except ValueError as e:
        logger.error(f"Date parsing error: {e}")
        return {"error": "Invalid date format provided."}, 400
    except SQLAlchemyError as e:
        logger.error(f"Database query error: {e}")
        return {"error": "An error occurred while fetching vehicle status events."}, 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": "An unexpected error occurred."}, 500
    finally:
        session.close()

def GetreportIncidentEvent(start_timestamp, end_timestamp):
    try:
        start_datetime = parse_date(start_timestamp)
        end_datetime = parse_date(end_timestamp)

        session = Session()
        events = session.query(IncidentEvent).filter(
            IncidentEvent.date_created >= start_datetime,
            IncidentEvent.date_created <= end_datetime
        ).all()
        events_list = [event.to_dict() for event in events]
        return events_list, 200
    except ValueError as e:
        logger.error(f"Date parsing error: {e}")
        return {"error": "Invalid date format provided."}, 400
    except SQLAlchemyError as e:
        logger.error(f"Database query error for IncidentEvent: {e}")
        return {"error": "An error occurred while fetching incident events."}, 500
    except Exception as e:
        logger.error(f"Unexpected error for IncidentEvent: {e}")
        return {"error": "An unexpected error occurred."}, 500
    finally:
        session.close()

# [V4] \/
def process_messages():
    """Process event messages from Kafka, excluding datetime from the payload."""
    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[str.encode(app_config['events']['topic'])]
    consumer = topic.get_simple_consumer(consumer_group=b'event_group', reset_offset_on_start=False, auto_offset_reset=OffsetType.LATEST)

    for message in consumer:
        if message is not None:
            msg_str = message.value.decode('utf-8')
            msg = json.loads(msg_str)
            logger.info(f"Consumed message: {msg}")
            payload = msg.get('payload', {})
            payload.pop('datetime', None)
            if msg["type"] == "VehicleStatusEvent":
                reportVehicleStatusEvent(payload)
            elif msg["type"] == "IncidentEvent":
                reportIncidentEvent(payload)
            consumer.commit_offsets()

app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api('Transit.yaml', strict_validation=True, validate_responses=True)

if __name__ == '__main__':
    logger.info("Starting Data Storage Service.")
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    logger.info("Data Storage Service successfully started. Now running Flask app.")
    app.run(port=8090)