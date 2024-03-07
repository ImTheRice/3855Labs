import connexion
import yaml
import uuid
import logging.config
from connexion import NoContent
import colorlog
from pykafka import KafkaClient
import json

# Enhanced logger setup
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

# Load configurations
with open('./app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())
with open('./log_conf.yaml', 'r') as f:
    logging.config.dictConfig(yaml.safe_load(f.read()))
    logger = logging.getLogger('basicLogger')
    logger.addHandler(color_handler)

# Kafka client setup
kafka_client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
kafka_topic = kafka_client.topics[str.encode(app_config['events']['topic'])]

def reportVehicleStatusEvent(body):
    """
    Produce Vehicle Status Event messages to Kafka.
    """
    if 'trace_id' not in body or not body['trace_id']:
        body['trace_id'] = str(uuid.uuid4())

    logger.info(f"Received Vehicle Status Event request with a trace id of {body['trace_id']}")

    producer = kafka_topic.get_sync_producer()
    message = {
        "type": "VehicleStatusEvent",
        "datetime": body.get("timestamp", ""),
        "payload": body
    }
    producer.produce(json.dumps(message).encode('utf-8'))

    logger.info(f"Produced Vehicle Status Event message with trace id {body['trace_id']}")

    return NoContent, 201

def reportIncidentEvent(body):
    """
    Produce Incident Event messages to Kafka.
    """
    if 'trace_id' not in body or not body['trace_id']:
        body['trace_id'] = str(uuid.uuid4())

    logger.info(f"Received Incident Event request with a trace id of {body['trace_id']}")

    producer = kafka_topic.get_sync_producer()
    message = {
        "type": "IncidentEvent",
        "datetime": body.get("timestamp", ""),
        "payload": body
    }
    producer.produce(json.dumps(message).encode('utf-8'))

    logger.info(f"Produced Incident Event message with trace id {body['trace_id']}")

    return NoContent, 201

# Placeholder functions for GET endpoints
def GetreportVehicleStatusEvent():
    pass

def GetreportIncidentEvent():
    pass

# FlaskApp setup
app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_api('Transit.yaml', strict_validation=True, validate_responses=True)

if __name__ == '__main__':
    app.run(port=8080)
