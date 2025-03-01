import logging
import sqlite3
import psycopg2
from model.trades import Trade
from model.messages import Message
from model.trade_updates import TradeUpdate

logger = logging.getLogger(__name__)

class dbHandler:
    def __init__(self, config):
        self.config = config
        self.host = config['DB']['HOST']
        self.port = config['DB']['PORT']
        self.dbname = config['DB']['DBNAME']
        self.user = config['DB']['USER']
        self.password = config['DB']['PASSWORD']
        self.db_config = {
            "host": self.host,  # Or use "postgres_db" if running inside another Docker container
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password
        }


    def _connect(self):
        """Connect to PostgreSQL and return the connection"""
        try:
            conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Connected to the database successfully!")
            return conn
        except psycopg2.Error as e:
            logger.error(f"❌ Error connecting to database: {e}")
            return None

    def create_tables(self, create_table_sqls):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            for create_table_sql in create_table_sqls.split('---'):
                cursor.execute(create_table_sql)
            conn.commit()
            logger.info("✅ Tables created successfully!")
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error creating tables: {e}")
            raise e
        finally:
            conn.close()

    def insert_message(self, message):
        """Save the Message instance to the database."""
        conn = self._connect()
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO messages (telegram_id, chat_id, timestamp, text, processed)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
        """
        try:
            # Execute the insert query with the instance's data
            cursor.execute(insert_query, (message.telegram_id, message.chat_id, message.timestamp, message.text, message.processed))
            conn.commit()

            # Fetch the ID of the newly inserted record
            new_record_id = cursor.fetchone()[0]
            logger.info(f"✅ Record added to 'messages' successfully with ID: {new_record_id}")
            return new_record_id  # Return the ID of the new record

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error adding record to 'messages': {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def get_message_by_id(self, telegram_id, chat_id):
        """Get a message by its ID."""
        conn = self._connect()
        cursor = conn.cursor()

        select_query = """SELECT * FROM messages WHERE telegram_id = %s AND chat_id = %s;"""
        try:
            cursor.execute(select_query,(int(telegram_id), str(chat_id),))
            record = cursor.fetchone()
            if record:
                logger.info(f"✅ Message found with ID: {telegram_id}")
                message = Message(telegram_id=record[1], chat_id=record[2], timestamp=record[3], text=record[4], processed=record[5])
                return message
            else:
                logger.warning(f"❌ Message not found with ID: {telegram_id}")
                return None
        except Exception as e:
            logger.error(f"❌ Error selecting message with ID {telegram_id}: {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def update_message(self, message_id, update_data):
        """
        Update the columns of a message dynamically based on the provided update data.
        :param message_id: The ID of the message to update.
        :param update_data: A dictionary containing the columns and their new values to update.
        """
        conn = self._connect()  # Establish connection
        cursor = conn.cursor()

        # Dynamically create the SET clause and values tuple
        set_clause = ', '.join([f"{key} = %s" for key in update_data.keys()])
        values = tuple(update_data.values()) + (message_id,)  # Add message_id as the last value for WHERE clause

        update_query = f"""
            UPDATE messages
            SET {set_clause}
            WHERE id = %s;
        """

        try:
            # Execute the update query
            cursor.execute(update_query, values)
            conn.commit()

            # Check if the update was successful (rows affected)
            if cursor.rowcount > 0:
                logger.info(f"✅ Message with ID {message_id} updated successfully.")
            else:
                logger.warning(f"⚠️ No message found with ID {message_id}. No update made.")

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error updating message with ID {message_id}: {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def insert_trade(self, trade):
        """Save the Message instance to the database."""
        conn = self._connect()
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO messages (asset, type, entry, stop_loss, take_profit, break_even, status, order_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
        """
        try:
            # Execute the insert query with the instance's data
            cursor.execute(insert_query, (trade.asset, trade.type, trade.entry, trade.stop_loss, trade.take_profit, trade.break_even, trade.status, trade.order_id))
            conn.commit()

            # Fetch the ID of the newly inserted record
            new_record_id = cursor.fetchone()[0]
            logger.info(f"✅ Record added to 'messages' successfully with ID: {new_record_id}")
            return new_record_id  # Return the ID of the new record

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error adding record to 'messages': {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection