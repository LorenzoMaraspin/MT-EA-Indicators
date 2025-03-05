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
                message = Message(id=record[0],telegram_id=record[1], timestamp=record[2], text=record[3], processed=record[4], chat_id=record[5])
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

    def update_message(self, update_data):
        """
        Update the columns of a message dynamically based on the provided update data.
        :param message_id: The ID of the message to update.
        :param update_data: A dictionary containing the columns and their new values to update.
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
        """Fetch the latest message and its associated trades."""
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
        """Save the Message instance to the database."""
        conn = self._connect()
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO trades (asset, type, entry, stop_loss, take_profits, break_even, status, order_id, message_id, volume)
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
        """Get a message by its ID."""
        conn = self._connect()
        cursor = conn.cursor()
        response = []
        select_query = """SELECT * FROM trades WHERE message_id = %s;"""
        try:
            cursor.execute(select_query,(message_id,))
            records = cursor.fetchall()
            if records:
                logger.info(f"✅ Message found with ID: {message_id}")
                for record in records:
                    trade = Trade(id=record[0], message_id=record[1], asset=record[2], type=record[3], entry=record[4], stop_loss=record[5], take_profit=record[6], status=record[7], break_even=record[8], order_id=record[9], volume=record[10])
                    response.append(trade)
                return response
            else:
                logger.warning(f"❌ Message not found with ID: {message_id}")
                return None
        except Exception as e:
            logger.error(f"❌ Error selecting message with ID {message_id}: {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def insert_trade_update(self, trade_update):
        """Save the Message instance to the database."""
        conn = self._connect()
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO trade_updates (trade_id, update_text, new_value)
            VALUES (%s, %s, %s) RETURNING id;
        """
        try:
            # Execute the insert query with the instance's data
            cursor.execute(insert_query, (trade_update.trade_id, trade_update.update_text, trade_update.new_value))
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
        :param message_id: The ID of the message to update.
        :param update_data: A dictionary containing the columns and their new values to update.
        """
        conn = self._connect()  # Establish connection
        cursor = conn.cursor()
        trade_dict = update_data.to_dict()
        # Dynamically create the SET clause and values tuple
        set_clause = ', '.join([f"{key} = %s" for key in trade_dict.keys()])
        values = tuple(trade_dict.values()) + (update_data.id, str(update_data.message_id),str(update_data.message_id),str(update_data.order_id))  # Add message_id as the last value for WHERE clause

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