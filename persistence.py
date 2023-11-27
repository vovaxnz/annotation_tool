import sqlite3
from typing import Dict
from core import Rectangle


class SQLiteAdapter:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None
        self.cursor = None

    def connect(self):
        """ Establish a connection to the SQLite database. """
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
            self.initialize_database()
        except sqlite3.Error as e:
            print(f"An error occurred while connecting to the database: {e}")

    def initialize_database(self):
        """ Initialize the database by creating necessary tables. """
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rectangles'")
            if not self.cursor.fetchone():
                create_table_query = """
                    CREATE TABLE IF NOT EXISTS rectangles (
                        id INTEGER PRIMARY KEY,
                        h FLOAT NOT NULL,
                        w FLOAT NOT NULL,
                        xc FLOAT NOT NULL,
                        yc FLOAT NOT NULL,
                        angle FLOAT NOT NULL
                    );
                """
                self.cursor.execute(create_table_query)
                self.connection.commit()
        except sqlite3.Error as e:
            print(f"An error occurred while initializing the database: {e}")

    def close(self):
        """ Close the connection to the SQLite database. """
        try:
            if self.cursor is not None:
                self.cursor.close()
            if self.connection is not None:
                self.connection.close()
        except sqlite3.Error as e:
            print(f"An error occurred while closing the database connection: {e}")

    def execute_query(self, query, params=None):
        """
        Execute a given SQL query with optional parameters.

        :param query: The SQL query to execute.
        :param params: Optional parameters for the query.
        """
        try:
            self.cursor.execute(query, params or ())
            self.connection.commit()
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print("An error occurred:", e.args[0])


class ModelSerializer:
    @staticmethod
    def serialize(rectangle: Rectangle) -> dict:
        # Convert the Rectangle object into a storable format
        data = {
            'h': rectangle.h,
            'w': rectangle.w,
            'xc': rectangle.xc,
            'yc': rectangle.yc,
            'angle': rectangle.angle,
        }
        return data  

    @staticmethod
    def deserialize(data: Dict) -> Rectangle:
        # Convert the stored format back into a Rectangle object
        return Rectangle(h=data['h'], w=data['w'], xc=data['xc'], xy=data['xy'], angle=data['angle'])


class DatabaseManager:
    def __init__(self, db_path):
        self.db_adapter = SQLiteAdapter(db_path)
        self.db_adapter.connect()

    def saveRectangleData(self, rectangle: Rectangle):
        # Insert or update the rectangle data in the database
        query = "INSERT INTO rectangles (h, w, xc, yc, angle) VALUES (?, ?, ?, ?, ?)"
        self.db_adapter.execute_query(query, (rectangle.h, rectangle.w, rectangle.xc, rectangle.yc, rectangle.angle))

    def loadRectangleData(self):
        # Load all rectangle data from the database
        query = "SELECT data FROM rectangles"
        rows = self.db_adapter.execute_query(query)

        # Deserialize the data into Rectangle objects
        rectangles = [ModelSerializer.deserialize(row[0]) for row in rows]
        return rectangles
    
    def close(self):
        self.db_adapter.close()
