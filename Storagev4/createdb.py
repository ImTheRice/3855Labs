import mysql.connector
from mysql.connector import Error

def create_database():
    try:
        connection = mysql.connector.connect(
            host='acit3855group4kafka.eastus2.cloudapp.azure.com',
            user='imricebowl',  # Adjust as per your configuration
            password='imricebowl'  # Adjust as per your configuration
        )
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS events")
        print("Database `events` created successfully.")
    except Error as e:
        print(f"Error creating database: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    create_database()
