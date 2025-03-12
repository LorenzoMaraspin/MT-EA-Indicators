import logging
import sqlite3
from http.client import responses

import psycopg2
from model.trades import Trade
from model.messages import Message
from model.trade_updates import TradeUpdate

logger = logging.getLogger(__name__)

class dbHandler:
    def __init__(self, config):
        """
        Initialize the dbHandler with the given configuration.

        Args:
            config (dict): A dictionary containing database configuration.
        """
        self.config = config
        self.db_env = "DB_DEV" if self.config['ENV'] == 'DEV' else "DB"
        self.host = config[self.db_env]['HOST']
        self.port = config[self.db_env]['PORT']
        self.dbname = config[self.db_env]['DBNAME']
        self.user = config[self.db_env]['USER']
        self.password = config[self.db_env]['PASSWORD']
        self.db_config = {
            "host": self.host,  # Or use "postgres_db" if running inside another Docker container
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password
        }

    def _connect(self):
        """
        Connect to PostgreSQL and return the connection.

        Returns:
            connection: A connection object to the PostgreSQL database.
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Connected to the database successfully!")
            return conn
        except psycopg2.Error as e:
            logger.error(f"❌ Error connecting to database: {e}")
            return None

    def create_tables(self, create_table_sqls):
        """
        Create tables in the database using the provided SQL statements.

        Args:
            create_table_sqls (str): A string containing SQL statements to create tables, separated by '---'.

        Raises:
            Exception: If there is an error during table creation.
        """
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
        """
        Save the Message instance to the database.

        Args:
            message (Message): An instance of the Message class to be saved.

        Returns:
            int: The ID of the newly inserted message.

        Raises:
            Exception: If there is an error during the insert operation.
        """
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
        """
        Retrieve a message by its Telegram ID and chat ID.

        Args:
            telegram_id (int): The Telegram ID of the message.
            chat_id (str): The chat ID associated with the message.

        Returns:
            Message: An instance of the Message class if found, otherwise None.

        Raises:
            Exception: If there is an error during the database query.
        """
        conn = self._connect()  # Establish a connection to the database
        cursor = conn.cursor()  # Create a cursor object to interact with the database

        select_query = """SELECT * FROM messages WHERE telegram_id = %s AND chat_id = %s;"""
        try:
            # Execute the SELECT query with the provided telegram_id and chat_id
            cursor.execute(select_query, (int(telegram_id), str(chat_id),))
            record = cursor.fetchone()  # Fetch the first matching record

            if record:
                # If a record is found, log the success and create a Message instance
                logger.info(f"✅ Message found with ID: {telegram_id} from chat: {chat_id}")
                message = Message(id=record[0], telegram_id=record[1], timestamp=record[2], text=record[3], processed=record[4], chat_id=record[5])
                return message
            else:
                # If no record is found, log a warning and return None
                logger.warning(f"❌ Message not found with ID: {telegram_id}")
                return None
        except Exception as e:
            # Log any exceptions that occur during the query
            logger.error(f"❌ Error selecting message with ID {telegram_id}: {e}")
            raise e
        finally:
            # Ensure the cursor and connection are closed
            cursor.close()
            conn.close()

    def update_message(self, update_data):
        """
        Update the columns of a message dynamically based on the provided update data.

        Args:
            update_data (Message): An instance of the Message class containing updated data.

        Raises:
            Exception: If there is an error during the update operation.
        """
        conn = self._connect()  # Establish connection
        cursor = conn.cursor()
        message_dict = update_data.to_dict()
        # Dynamically create the SET clause and values tuple
        set_clause = ', '.join([f"{key} = %s" for key in message_dict.keys()])
        values = tuple(message_dict.values()) + (update_data.telegram_id, str(update_data.chat_id),)  # Add message_id as the last value for WHERE clause

        update_query = f"""
            UPDATE messages
            SET {set_clause}
            WHERE telegram_id = %s and chat_id = %s;
        """

        try:
            # Execute the update query
            cursor.execute(update_query, values)
            conn.commit()

            # Check if the update was successful (rows affected)
            if cursor.rowcount > 0:
                logger.info(f"✅ Message with ID {update_data.telegram_id} updated successfully.")
            else:
                logger.warning(f"⚠️ No message found with ID {update_data.telegram_id}. No update made.")

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error updating message with ID {update_data.telegram_id}: {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def get_latest_message_with_trades(self):
        """
        Fetch the latest message and its associated trades.

        Returns:
            list: A list of Trade instances associated with the latest message, or None if no trades are found.

        Raises:
            Exception: If there is an error during the query.
        """
        conn = self._connect()
        cursor = conn.cursor()

        query = """
        SELECT t.*
        FROM Trades t
        JOIN (
            SELECT id FROM Messages ORDER BY id DESC LIMIT 1
        ) latest_message ON t.message_id = latest_message.id;
        """
        response = []
        try:
            cursor.execute(query)
            records = cursor.fetchall()  # Get the last inserted message's trade

            if records:
                logger.info("✅ Latest message and trade found.")
                for record in records:
                    trade = Trade(id=record[0], message_id=record[1], asset=record[2], type=record[3], entry=record[4], stop_loss=record[5], take_profit=record[6], status=record[7], break_even=record[8], order_id=record[9], volume=record[10])
                    response.append(trade)
                return response
            else:
                logger.warning("❌ No trades found for the latest message.")
                return None

        except Exception as e:
            logger.error(f"❌ Error fetching latest message with trades: {e}")
            raise e

        finally:
            cursor.close()
            conn.close()

    def insert_trade(self, trade):
        """
        Save the Trade instance to the database.

        Args:
            trade (Trade): An instance of the Trade class to be saved.

        Returns:
            int: The ID of the newly inserted trade.

        Raises:
            Exception: If there is an error during the insert operation.
        """
        conn = self._connect()
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO trades (asset, type, entry, stop_loss, take_profit, break_even, status, order_id, message_id, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """
        try:
            # Execute the insert query with the instance's data
            cursor.execute(insert_query, (trade.asset, trade.type, trade.entry, trade.stop_loss, trade.take_profit, trade.break_even, trade.status, trade.order_id, trade.message_id, trade.volume))
            conn.commit()

            # Fetch the ID of the newly inserted record
            new_record_id = cursor.fetchone()[0]
            logger.info(f"✅ Record added to 'trades' successfully with ID: {new_record_id}")
            return new_record_id  # Return the ID of the new record

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error adding record to 'trades': {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def get_trades_by_id(self, message_id):
        """
        Get trades by their message ID.

        Args:
            message_id (int): The message ID to filter trades.

        Returns:
            list: A list of Trade instances associated with the given message ID, or None if no trades are found.

        Raises:
            Exception: If there is an error during the query.
        """
        conn = self._connect()
        cursor = conn.cursor()
        response = []
        select_query = """SELECT * FROM trades WHERE message_id = %s;"""
        try:
            cursor.execute(select_query, (message_id,))
            records = cursor.fetchall()
            if records:
                logger.info(f"✅ Trade found with ID: {message_id}")
                for record in records:
                    trade = Trade(id=record[0], message_id=record[1], asset=record[2], type=record[3], entry=record[4], stop_loss=record[5], take_profit=record[6], status=record[7], break_even=record[8], order_id=record[9], volume=record[10])
                    response.append(trade)
                return response
            else:
                logger.warning(f"❌ Trade not found with ID: {message_id}")
                return None
        except Exception as e:
            logger.error(f"❌ Error selecting trade with ID {message_id}: {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def get_all_trades(self):
        """
        Get all trades with status 'open'.

        Returns:
            list: A list of Trade instances with status 'open', or None if no trades are found.

        Raises:
            Exception: If there is an error during the query.
        """
        logger.setLevel(logging.CRITICAL)
        conn = self._connect()
        cursor = conn.cursor()
        response = []
        select_query = """SELECT * FROM trades WHERE status = 'open';"""
        try:
            cursor.execute(select_query)
            records = cursor.fetchall()
            if records:
                logger.info(f"✅ Trade found")
                for record in records:
                    trade = Trade(id=record[0], message_id=record[1], asset=record[2], type=record[3], entry=record[4], stop_loss=record[5], take_profit=record[6], status=record[7], break_even=record[8], order_id=record[9], volume=record[10])
                    response.append(trade)
                return response
            else:
                logger.warning(f"❌ Trade not found")
                return None
        except Exception as e:
            logger.error(f"❌ Error selecting trade: {e}")
            raise e

        finally:
            logger.setLevel(logging.INFO)
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def insert_trade_update(self, trade_update):
        """
        Save the TradeUpdate instance to the database.

        Args:
            trade_update (TradeUpdate): An instance of the TradeUpdate class to be saved.

        Returns:
            int: The ID of the newly inserted trade update.

        Raises:
            Exception: If there is an error during the insert operation.
        """
        conn = self._connect()
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO trade_updates (trade_id, update_text, new_value, order_id)
            VALUES (%s, %s, %s, %s) RETURNING id;
        """
        try:
            # Execute the insert query with the instance's data
            cursor.execute(insert_query, (trade_update.trade_id, trade_update.update_text, trade_update.new_value, trade_update.order_id,))
            conn.commit()

            # Fetch the ID of the newly inserted record
            new_record_id = cursor.fetchone()[0]
            logger.info(f"✅ Record added to 'trade_updates' successfully with ID: {new_record_id}")
            return new_record_id  # Return the ID of the new record

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error adding record to 'trade_updates': {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def update_trade(self, update_data):
        """
        Update the columns of a trade dynamically based on the provided update data.

        Args:
            update_data (Trade): An instance of the Trade class containing updated data.

        Raises:
            Exception: If there is an error during the update operation.
        """
        conn = self._connect()  # Establish connection
        cursor = conn.cursor()
        trade_dict = update_data.to_dict()
        # Dynamically create the SET clause and values tuple
        set_clause = ', '.join([f"{key} = %s" for key in trade_dict.keys()])
        values = tuple(trade_dict.values()) + (update_data.id, update_data.message_id, str(update_data.order_id))  # Add message_id as the last value for WHERE clause

        update_query = f"""
            UPDATE trades
            SET {set_clause}
            WHERE id = %s and message_id = %s and order_id = %s;
        """

        try:
            # Execute the update query
            cursor.execute(update_query, values)
            conn.commit()

            # Check if the update was successful (rows affected)
            if cursor.rowcount > 0:
                logger.info(f"✅ Trade with ID {update_data.message_id} updated successfully.")
            else:
                logger.warning(f"⚠️ No trade found with ID {update_data.message_id}. No update made.")

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error updating trades with ID {update_data.message_id}: {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection