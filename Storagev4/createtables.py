import mysql.connector
from mysql.connector import Error

def create_tables():
    try:
        connection = mysql.connector.connect(
            host='acit3855group4kafka.eastus2.cloudapp.azure.com',
            user='superbaddefault',  
            password='superbaddefault', 
            database='events'
        )
        print(connection)

        cursor = connection.cursor()
        vehicle_status_events_table = """
        CREATE TABLE IF NOT EXISTS vehicle_status_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uuid VARCHAR(36) NOT NULL,
            distanceTravelled INT,
            timeToArrival VARCHAR(50),
            onTimeScore INT,
            userId VARCHAR(36),
            trace_id VARCHAR(36),
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        incident_events_table = """
        CREATE TABLE IF NOT EXISTS incident_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uuid VARCHAR(36) NOT NULL,
            incidentType VARCHAR(250) NOT NULL,
            incidentSeverity INT NOT NULL,
            expectedDuration VARCHAR(50) NOT NULL,
            userId VARCHAR(36) NOT NULL,
            trace_id VARCHAR(36) NOT NULL,
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(vehicle_status_events_table)
        cursor.execute(incident_events_table)
        print("Tables created successfully.")
    except Error as e:
        print(f"Error creating tables: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    create_tables()
