from abc import ABCMeta
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from typing import Optional

from sqlalchemy.sql import text  # For executing raw SQL statements
from sqlalchemy.ext.declarative import DeclarativeMeta
from config import settings

# Define a new metaclass that combines ABCMeta and DeclarativeMeta
class ABSQLAlchemyMeta(ABCMeta, DeclarativeMeta):
    pass

Base = declarative_base(metaclass=ABSQLAlchemyMeta)


session_configured = False

class SessionNotConfiguredException(Exception):
    """Custom exception to indicate the session is not configured."""
    pass


def get_session():
    """Session factory to ensure the session is configured before use."""
    if not session_configured:
        raise SessionNotConfiguredException("Session is not configured. Please run configure_database() before performing database operations.")
    return session


def configure_database(database_path):
    global session
    global session_configured

    database_path += "?check_same_thread=False" # To allow shared connection usage

    engine = create_engine(database_path)

    with engine.connect() as connection:

        # In SQLite's NORMAL mode, the engine ensures the rollback journal is securely written to disk for recovery purposes, 
        # but does not wait for the main database file updates to be confirmed, 
        # relying on the operating system to manage these writes.
        # This setting provides a reasonable balance between performance and durability
        connection.execute(text("PRAGMA synchronous = NORMAL")) 

        # Write-Ahead Logging (WAL) journal mode in SQLite
        # instead of writing changes directly to the main database file, SQLite writes these changes to a separate WAL file in a sequential manner.
        # When a transaction is committed, SQLite doesn’t immediately apply the changes in the WAL file to the main database file. 
        # Instead, the changes remain in the WAL file, and the database file is updated in the background 
        # or when the WAL file reaches a certain size
        connection.execute(text("PRAGMA journal_mode = WAL"))


    Base.metadata.create_all(engine)  # Make sure all tables are created
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    session_configured = True


