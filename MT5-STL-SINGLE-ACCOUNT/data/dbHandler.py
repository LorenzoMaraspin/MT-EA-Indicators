import logging
import psycopg2
from data.trade import Trade
from data.tg_message import Message
from data.tradeUpdate import TradeUpdate
from data.account import Account

logger = logging.getLogger(__name__)

class dbHandler:
    def __init__(self, config):
        """
        Initialize the dbHandler with the given configuration.

        Args:
            config (dict): A dictionary containing database configuration.
        """
        self.config = config
        self.host = config["DB"]['HOST']
        self.port = config["DB"]['PORT']
        self.dbname = config["DB"]['DBNAME']
        self.user = config["DB"]['USER']
        self.password = config["DB"]['PASSWORD']
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
# ======================================================================================================================
# MESSAGE
# ======================================================================================================================
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
            INSERT INTO tg_message (tg_msg_id, tg_chat_id, tg_src_chat_name,tg_dst_chat_id, tg_dst_msg_id, msg_body, msg_timestamp, msg_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING msg_id;
        """
        try:
            # Execute the insert query with the instance's data
            cursor.execute(insert_query, (
                message.tg_msg_id,
                message.tg_chat_id,
                message.tg_src_chat_name,
                message.tg_dst_chat_id,
                message.tg_dst_msg_id,
                message.msg_body,
                message.msg_timestamp,
                message.msg_status
            ))
            conn.commit()

            # Fetch the ID of the newly inserted record
            new_record_id = cursor.fetchone()[0]
            logger.info(f"✅ Record added to 'tg_message' successfully with ID: {new_record_id}")
            return new_record_id  # Return the ID of the new record

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error adding record to 'messages': {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def get_message_by_id(self, tg_msg_id, tg_chat_id):
        """
        Retrieve a message by its Telegram ID and chat ID.

        Args:
            tg_msg_id (int): The Telegram ID of the message.
            tg_chat_id (int): The chat ID associated with the message.

        Returns:
            Message: An instance of the Message class if found, otherwise None.

        Raises:
            Exception: If there is an error during the database query.
        """
        conn = self._connect()  # Establish a connection to the database
        cursor = conn.cursor()  # Create a cursor object to interact with the database

        select_query = """SELECT * FROM tg_message WHERE tg_msg_id = %s AND tg_chat_id = %s;"""
        try:
            # Execute the SELECT query with the provided telegram_id and chat_id
            cursor.execute(select_query, (int(tg_msg_id), str(tg_chat_id),))
            record = cursor.fetchone()  # Fetch the first matching record

            if record:
                # If a record is found, log the success and create a Message instance
                logger.info(f"✅ Message found with ID: {tg_chat_id} from chat: {tg_chat_id}")
                message = Message(
                    msg_id=record[0],
                    tg_msg_id=record[1],
                    tg_chat_id=record[2],
                    tg_src_chat_name=record[3],
                    tg_dst_chat_id=record[4],
                    tg_dst_msg_id=record[5],
                    msg_body=record[6],
                    msg_timestamp=record[7],
                    msg_status=record[8]
                )
                return message
            else:
                # If no record is found, log a warning and return None
                logger.warning(f"❌ Message not found with ID: {tg_chat_id}")
                return None
        except Exception as e:
            # Log any exceptions that occur during the query
            logger.error(f"❌ Error selecting message with ID {tg_chat_id}: {e}")
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
        values = tuple(message_dict.values()) + (update_data.tg_msg_id, str(update_data.tg_chat_id),)

        update_query = f"""
            UPDATE tg_message
            SET {set_clause}
            WHERE tg_msg_id = %s and tg_chat_id = %s;
        """

        try:
            # Execute the update query
            cursor.execute(update_query, values)
            conn.commit()

            # Check if the update was successful (rows affected)
            if cursor.rowcount > 0:
                logger.info(f"✅ Message with ID {update_data.tg_msg_id} updated successfully.")
            else:
                logger.warning(f"⚠️ No message found with ID {update_data.tg_msg_id}. No update made.")

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error updating message with ID {update_data.tg_msg_id}: {e}")
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
                    trade = Trade(id=record[0], message_id=record[1], asset=record[2], type=record[3], entry=record[4], stop_loss=record[5], take_profit=record[6], status=record[7], break_even=record[8], order_id=record[9], volume=record[10], account_id=record[11])
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
# ======================================================================================================================
# TRADE
# ======================================================================================================================
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
            INSERT INTO trade (msg_id, order_id, account_id, symbol, direction, entry_price, stop_loss, take_profit, break_even, volume, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING trade_id;
        """
        try:
            # Execute the insert query with the instance's data
            cursor.execute(insert_query, (
                trade.msg_id,
                trade.order_id,
                trade.account_id,
                trade.symbol,
                trade.direction,
                trade.entry_price,
                trade.stop_loss,
                trade.take_profit,
                trade.break_even,
                trade.volume,
                trade.status))
            conn.commit()

            # Fetch the ID of the newly inserted record
            new_record_id = cursor.fetchone()[0]
            logger.info(f"✅ Record added to 'trade' successfully with ID: {new_record_id}")
            return new_record_id  # Return the ID of the new record

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error adding record to 'trade': {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def get_trades_by_id(self, msg_id):
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
        select_query = """SELECT * FROM trade WHERE msg_id = %s;"""
        try:
            cursor.execute(select_query, (msg_id,))
            records = cursor.fetchall()
            if records:
                logger.info(f"✅ Trade found with ID: {msg_id}")
                for record in records:
                    trade = Trade(trade_id=record[0], msg_id=record[1], order_id=record[2], account_id=record[3], symbol=record[4], direction=record[5], entry_price=record[6], stop_loss=record[7], take_profit=record[8], break_even=record[9], volume=record[10], status=record[11])
                    response.append(trade)
                return response
            else:
                logger.warning(f"❌ Trade not found with ID: {msg_id}")
                return None
        except Exception as e:
            logger.error(f"❌ Error selecting trade with ID {msg_id}: {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def get_all_trades(self, account_id):
        """
        Get all trades with status 'open'.

        Returns:
            dict: A dictionary where each key is a msg_id and the value is a list of Trade instances with that msg_id,
                  or None if no trades are found.

        Raises:
            Exception: If there is an error during the query.
        """
        logger.setLevel(logging.CRITICAL)
        conn = self._connect()
        cursor = conn.cursor()
        response = {}
        select_query = """SELECT * FROM trade WHERE status = 'open' and account_id = %s;"""
        try:
            cursor.execute(select_query, (account_id,))
            records = cursor.fetchall()
            if records:
                logger.info(f"✅ Trade found")
                for record in records:
                    trade = Trade(
                        trade_id=record[0],
                        msg_id=record[1],
                        order_id=record[2],
                        account_id=record[3],
                        symbol=record[4],
                        direction=record[5],
                        entry_price=record[6],
                        stop_loss=record[7],
                        take_profit=record[8],
                        break_even=record[9],
                        volume=record[10],
                        status=record[11]
                    )
                    if trade.msg_id in response:
                        response[trade.msg_id].append(trade)
                    else:
                        response[trade.msg_id] = [trade]
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
        values = tuple(trade_dict.values()) + (update_data.trade_id, update_data.msg_id, int(update_data.order_id))  # Add message_id as the last value for WHERE clause

        update_query = f"""
            UPDATE trade
            SET {set_clause}
            WHERE trade_id = %s and msg_id = %s and order_id = %s;
        """

        try:
            # Execute the update query
            cursor.execute(update_query, values)
            conn.commit()

            # Check if the update was successful (rows affected)
            if cursor.rowcount > 0:
                logger.info(f"✅ Trade with ID {update_data.msg_id} updated successfully.")
            else:
                logger.warning(f"⚠️ No trade found with ID {update_data.msg_id}. No update made.")

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error updating trades with ID {update_data.msg_id}: {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

    def get_open_trades_based_on_src_tg_chat(self, tg_src_chat_name):
        conn = self._connect()
        cursor = conn.cursor()

        query = """
                select * from trade t join tg_message tm on t.msg_id = tm.msg_id where t.status = 'open' and tm.tg_src_chat_name = %s;
                """
        response = []
        try:
            cursor.execute(query, (tg_src_chat_name,))
            records = cursor.fetchall()

            if records:
                logger.info(f"✅ Trade found with ID: {tg_src_chat_name}")
                for record in records:
                    trade = Trade(trade_id=record[0], msg_id=record[1], order_id=record[2], account_id=record[3],
                                  symbol=record[4], direction=record[5], entry_price=record[6], stop_loss=record[7],
                                  take_profit=record[8], break_even=record[9], volume=record[10], status=record[11])
                    response.append(trade)
                return response
            else:
                logger.warning(f"❌ Trade not found with ID: {tg_src_chat_name}")
                return None

        except Exception as e:
            logger.error(f"❌ Error fetching latest message with trades: {e}")
            raise e

        finally:
            cursor.close()
            conn.close()
# ======================================================================================================================
# TRADE UPDATE
# ======================================================================================================================
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
        if isinstance(trade_update, list):
            values = [(tu.trade_id, tu.order_id, tu.account_id, tu.update_action, tu.update_body) for tu in trade_update]
        else:
            values = (trade_update.trade_id, trade_update.order_id, trade_update.account_id, trade_update.update_action,
             trade_update.update_body,)
        insert_query = """
            INSERT INTO tradeupdate (trade_id, order_id, account_id, update_action, update_body)
            VALUES (%s, %s, %s, %s, %s) RETURNING trade_update_id;
        """
        try:
            # Execute the insert query with the instance's data
            if isinstance(trade_update, list):
                records = []
                for tu in trade_update:
                    cursor.execute(insert_query,
                                   (tu.trade_id, tu.order_id, tu.account_id, tu.update_action, tu.update_body))
                    records.append(cursor.fetchone()[0])
                conn.commit()
                logger.info(f"✅ Records added to 'tradeupdate' successfully with IDs: {records}")
            else:
                cursor.execute(insert_query, values)
                conn.commit()
                records = cursor.fetchone()[0]
            return records

        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error adding record to 'tradeupdate': {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection
# ======================================================================================================================
# ACCOUNT
# ======================================================================================================================
    def get_software_account_based_on_id(self, account_id):
        """
        Retrieve a software account by its ID.

        Args:
            account_id (int): The ID of the account to retrieve.

        Returns:
            Account: An instance of the Account class if found, otherwise None.

        Raises:
            Exception: If there is an error during the database query.
        """
        conn = self._connect()
        cursor = conn.cursor()
        select_query = """
        SELECT
            a.mt5_account_id,
            a.mt5_server,
            a.mt5_broker,
            a.mt5_balance,
            a.mt5_password,
            a.environment,
            a.tg_id,
            a.tg_phone,
            a.tg_channels,
            a.tg_session,
            a.tg_hash,
        COALESCE(
            json_agg(
                json_build_object(
                    'instrument', bsc.instrument,
                    'symbol', bsc.symbol,
                    'n_trades', bsc.n_trades,
                    'lot_size', bsc.lot_size
                )
            ) FILTER (WHERE bc.id IS NOT NULL), '[]'
        ) AS symbol_configurations
        FROM
            account a
        LEFT JOIN broker_config bc ON a.mt5_account_id = bc.account_id
        LEFT JOIN broker_symbol_config bsc ON bc.id = bsc.broker_config_id
        WHERE
            a.mt5_account_id = %s
        GROUP BY
            a.mt5_account_id,
            a.mt5_server,
            a.mt5_broker,
            a.mt5_balance,
            a.mt5_password,
            a.environment,
            a.tg_id,
            a.tg_phone,
            a.tg_channels,
            a.tg_session,
            a.tg_hash;
        """
        try:
            # Execute the SELECT query with the provided account_id
            cursor.execute(select_query, (account_id,))
            record = cursor.fetchone()  # Fetch the first matching record

            if record:
                # If a record is found, log the success and create an Account instance
                logger.info(f"✅ Account found with ID: {account_id}")
                account = Account(mt5_account_id=record[0], mt5_server=record[1], mt5_broker=record[2], mt5_balance=record[3], mt5_password=record[4],environment=record[5], tg_id=record[6], tg_phone=record[7], tg_channels=record[8], tg_session=record[9], tg_hash=record[10], symbol_config=record[11])
                return account
            else:
                # If no record is found, log a warning and return None
                logger.warning(f"❌ Account not found with ID: {account_id}")
                return None
        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error getting account with id {account_id}: {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection
    def get_software_accounts_based_on_env(self, env):
        """
        Update the columns of a trade dynamically based on the provided update data.

        Args:
            env (str): Environment value to get the account list

        Raises:
            Exception: If there is an error during the update operation.
        """
        conn = self._connect()  # Establish connection
        cursor = conn.cursor()

        response = []
        select_query = """select * from account where account.environment = %s;"""
        try:
            cursor.execute(select_query, (env,))
            records = cursor.fetchall()
            if records:
                logger.info(f"✅ Account found with environment: {env}")
                for record in records:
                    account = Account(mt5_account_id=record[0], mt5_server=record[1], mt5_broker=record[2], mt5_balance=record[3], mt5_password=record[4],environment=record[5], tg_id=record[6], tg_phone=record[7], tg_channels=record[8], tg_session=record[9], tg_hash=record[10])
                    response.append(account)
                return response
            else:
                logger.warning(f"❌ Account not found with env: {env}")
                return None
        except Exception as e:
            conn.rollback()  # Rollback in case of error
            logger.error(f"❌ Error getting account with env {env}: {e}")
            raise e

        finally:
            cursor.close()  # Close the cursor
            conn.close()  # Close the connection