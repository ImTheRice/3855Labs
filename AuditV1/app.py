import connexion
import yaml
import json
import logging.config
from pykafka import KafkaClient

app_conf_file = "app_conf.yaml"
log_conf_file = "log_conf.yaml"

# Load configurations
with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

# Ensure logger is set to debug level
logger.setLevel(logging.DEBUG)

logger.info(f"App Conf File: {app_conf_file}")
logger.info(f"Log Conf File: {log_conf_file}")

# Function to retrieve a Vehicle Status event by index
def get_vehicle_status_event(index):
    logger.debug("Entering get_vehicle_status_event function")
    try:
        hostname = f'{app_config["events"]["hostname"]}:{app_config["events"]["port"]}'
        client = KafkaClient(hosts=hostname)
        topic = client.topics[str.encode(app_config["events"]["topic"])]
        consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
        logger.debug("Kafka consumer initialized")

        count = 0
        for msg in consumer:
            if msg is not None and msg.value:
                msg_str = msg.value.decode('utf-8').strip()
                if msg_str:  # Check if msg_str is not empty
                    try:
                        msg = json.loads(msg_str)
                        if msg["type"] == "VehicleStatusEvent":
                            if count == index:
                                logger.info(f"Vehicle Status Event found at index {index}")
                                return msg["payload"], 200
                            count += 1
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decoding error: {e} - Message string: '{msg_str}'")
                        continue  # Skip this message and continue with the next
    except Exception as e:
        logger.error(f"Error retrieving Vehicle Status Event: {e}", exc_info=True)
    logger.error(f"Could not find Vehicle Status Event at index {index}")
    return {"message": "Not Found"}, 404

def get_incident_event(index):
    logger.debug("Entering get_incident_event function")
    try:
        hostname = f'{app_config["events"]["hostname"]}:{app_config["events"]["port"]}'
        client = KafkaClient(hosts=hostname)
        topic = client.topics[str.encode(app_config["events"]["topic"])]
        consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
        logger.debug("Kafka consumer initialized")

        count = 0
        for msg in consumer:
            if msg is not None and msg.value:
                msg_str = msg.value.decode('utf-8').strip()
                if msg_str:  # Check if msg_str is not empty
                    try:
                        msg = json.loads(msg_str)
                        if msg["type"] == "IncidentEvent":
                            if count == index:
                                logger.info(f"Incident Event found at index {index}")
                                return msg["payload"], 200
                            count += 1
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decoding error: {e} - Message string: '{msg_str}'")
                        continue  # Skip this message and continue with the next
    except Exception as e:
        logger.error(f"Error retrieving Incident Event: {e}", exc_info=True)
    logger.error(f"Could not find Incident Event at index {index}")
    return {"message": "Not Found"}, 404

app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api('Transit.yaml', strict_validation=True, validate_responses=True)

if __name__ == '__main__':
    logger.debug("Starting application on port 8110")
    app.run(port=8110)
