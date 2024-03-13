import mysql.connector
from mysql.connector import Error

def create_database():
    try:
        connection=None
        connection = mysql.connector.connect(
            host='localhost',
            user='superbaddefault', 
            password='superbaddefault'  
        )
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS events")
        print("Database `events` created successfully.")

        cursor.execute("GRANT ALL PRIVILEGES ON events.* TO 'superbaddefault'@'%'")
        cursor.execute("FLUSH PRIVILEGES")
        print("Granted all privileges to user 'superbaddefault' on database `events`.")

    except Error as e:
        print(f"Error creating database: {e}")
    finally:
        print("Done with CreateDB")
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    create_database()
