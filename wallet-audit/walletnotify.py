#!/usr/bin/env python3.5
import pymysql.cursors
import sys
import json
import requests
import os
from utils import parsing, output
# 0.2.0a-Rw: Aareon Sullivan 2017


class Query_db():
    def __init__(self, config):
        config_mysql = config["mysql"]
        host = config_mysql["db_host"]
        try:
            port = int(config_mysql["db_port"])
        except KeyError:
            port = 3306
        db_user = config_mysql["db_user"]
        db_pass = config_mysql["db_pass"]
        db = config_mysql["db"]
        self.connection = pymysql.connect(
            host=host,
            port=port,
            user=db_user,
            password=db_pass,
            db=db)

    def select(self, query_array, query_dict, query_from, method):
        query = "SELECT "
        for item in query_array:
            query = query + item + ","
            query = query[:-1]

        query = query + " FROM " + query_from + " WHERE "
        for key, value in query_dict.items():
            query = query + "`" + key + "` = '" + str(value) + "' AND"
        query = query[:-3]
        result_set = self.execute(query, method)
        return result_set

    def update(self, query_dict_column, query_dict_row, query_from):
        query = "UPDATE `" + query_from + "` SET "
        for key, value in query_dict_row.items():
            query = query + "`" + key + "` = '" + str(value) + "', "
        query = query[:-2]
        query = query + " WHERE "

        for key, value in query_dict_column.items():
            query = query + "`" + key + "` = '" + str(value) + "'"
        self.execute(query, "commit")
        return

    def insert(self, query_dict, query_from):
        query = "INSERT INTO `" + query_from + "` ("
        for key, value in query_dict.items():
            query = query + "`" + key + "`, "
        query = query[:-2] + ") VALUES ("

        for key, value in query_dict.items():
            query = query + "'" + str(value) + "', "
        query = query[:-2] + ")"
        self.execute(query, "commit")
        return

    def delete(self, query_dict, query_from):
        query = "DELETE FROM `" + query_from + "` WHERE "
        for key, value in query_dict.items():
            query = query + "`" + key + "` = '" + str(value) + "' AND "
        query = query[:-4] + "LIMIT 1"
        self.execute(query, "commit")
        return

    def execute(self, query, method):
        # Create cursor and execute query
        cursor = self.connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query)
        # Follow up actions based on method passed
        if method == "commit":
            self.connection.commit()
            cursor.close()
        if method == "fetchone":
            result_set = cursor.fetchone()
            cursor.close()
            return result_set
        if method == "rowcount":
            result_set = cursor.rowcount
            cursor.close()
            return result_set


class Walletnotify:
    def check_txs(self, config, txid, transactions):
        self.coin = config["coin"]
        self.txid = txid
        # Loop through all transactions
        for transaction in transactions["details"]:
            # Set confirmations to pass
            confirmations = transactions["confirmations"]
            # Point transaction to appropriate function
            if transaction["category"] == "send":
                self.check_send(transaction, confirmations)
            else:
                self.check_received(transaction, confirmations)

    def check_send(self, transaction, confirmations):
        if confirmations == 0:
            # Build dictionary and array for selecting user's balance in "db"
            #"""SELECT balance WHERE snowflake = transaction["account"]"""
            result_set = query.select(
                ["balance"], {'snowflake': transaction["account"]}, "db", "fetchone")

            rowcount = query.select(["txid"], {
                                      'txid': self.txid, 'account': transaction["account"]}, "unconfirmed", "rowcount")

            # If the returned rowcount is less than 1
            # Insert the transaction into "unconfirmed"
            if rowcount < 1:

                #"""INSERT INTO "unconfirmed" (account, amount, category, txid) VALUES (
                # transaction["account"], transaction["amount"],
                # transaction["category"], self.txid)"""
                query.({'account': transaction["account"], 'amount': transaction["amount"],
                                'category': transaction["category"], 'txid': self.txid}, "unconfirmed")

                # Create new balance from user's old balance minus the amount
                # in send (by adding a negative number)
                new_balance = float(
                    result_set["balance"]) + float(transaction["amount"])

                # Update user's balance with new information
                #"""UPDATE "db" SET balance = new_balance, lasttxid = self.txid WHERE snowflake = transaction["account"]"""
                query.update({'snowflake': transaction["account"]}, {
                               'balance': new_balance, 'lasttxid': self.txid}, "db")

                # Display message on completion with transaction account and
                # new balance
                message = """{}: SEND (unconfirmed); account: {},
                new balance: {}, amount: {}""".format(self.coin, transaction["account"], new_balance, transaction["amount"])
                output.success(message)
        else:
            #"""DELETE FROM "unconfirmed"
            # WHERE account = transaction["account"], amount = transaction["amount"],
            # category = "transaction["category"], txid = self.txid"""
            # If "send" transaction confirms, remove from "unconfirmed"
            query.delete({'account': transaction["account"], 'amount': transaction["amount"],
                            'category': transaction["category"], 'txid': self.txid}, "unconfirmed")
            message = """{}: SEND (confirmed); account: {},
            amount: {}""".format(self.coin, transaction["account"], transaction["amount"])
            output.success(message)
        return

    def check_received(self, transaction, confirmations):
        if confirmations == 0:
            # Build dictionary and array for selecting transaction in "unconfirmed"
            #"""SELECT txid WHERE txid = self.txid AND account = transaction["account"]"""
            # Get number of rows that are identical to this query
            rowcount = query.select(["txid"], {
                                      'txid': self.txid, 'account': transaction["account"]}, "unconfirmed", "rowcount")

            # If the returned rowcount is less than 1
            # Insert the transaction into "unconfirmed"
            if rowcount == 1:

                #"""INSERT INTO "unconfirmed" (account, amount, category, txid) VALUES (
                # transaction["account"], transaction["amount"],
                # transaction["category"], self.txid)"""
                query.({'account': transaction["account"], 'amount': transaction["amount"],
                                'category': transaction["category"], 'txid': self.txid}, "unconfirmed")

                message = """{}: {} (unconfirmed); account: {},
                amount: {}""".format(self.coin, transaction["category"].upper(), transaction["account"], transaction["amount"])
                output.success(message)
        else:

            #"""DELETE FROM "unconfirmed"
            # WHERE account = transaction["account"], amount = transaction["amount"],
            # category = "transaction["category"], txid = self.txid"""
            query.delete({'account': transaction["account"], 'amount': transaction["amount"],
                            'category': transaction["category"], 'txid': self.txid}, "unconfirmed")

            # Calculate new balance and which columns to update_balance
            # Check if transaction was generated (staked)
            if transaction["category"] == "generate":
                # SELECT balance and staked from "db" WHERE snowflake is equal
                # to transaction["account"]
                result_set = query.select(["balance", "staked"], {
                                            'snowflake': transaction["account"]}, "db", "fetchone")

                new_balance = float(
                    result_set["balance"]) + float(transaction["amount"])

                new_staked = float(
                    result_set["balance"]) + float(transaction["amount"])

                # Set dict for updating in case of generated (staked)
                dict_for_column_update = {
                    'balance': new_balance, 'staked': new_staked, 'lasttxid': self.txid}

                #"""UPDATE "db"
                # SET balance = new_balance (staked = new_staked)
                # WHERE snowflake = transaction["account"]"""
                query.update(
                    {'snowflake': transaction["account"]}, dict_for_column_update, "db")

            else:
                # SELECT balance from "db" WHERE snowflake is equal to
                # transaction["account"]
                result_set = query.select(
                    ["balance"], {'snowflake': transaction["account"]}, "db", "fetchone")

                # If transaction category is "received"
                new_balance = float(
                    result_set["balance"]) + float(transaction["amount"])

                # Set dict for updating in case of "received"
                dict_for_column_update = {
                    'balance': new_balance, 'lasttxid': self.txid}

                #"""UPDATE "db"
                # SET balance = new_balance (staked = new_staked)
                # WHERE snowflake = transaction["account"]"""
                query.update(
                    {'snowflake': transaction["account"]}, dict_for_column_update, "db")

            message = """{}: {} (confirmed); account: {},
            new balance: {}, amount: {}""".format(self.coin, transaction["category"].upper(),transaction["account"], new_balance, transaction["amount"])
            output.success(message)
        return

    def update_balance(self, transaction):
        # Build dictionary and array for selecting user's balance in "db"
        #"""SELECT balance WHERE snowflake = transaction["account"]"""
        result_set = query.select(
            ["balance"], {'snowflake': transaction["account"]}, "db", "fetchone")

        if transaction["category"] != "generated":
            new_balance = float(
                result_set["balance"]) + float(transaction["amount"])

            # Update user's balance with new information
            #"""UPDATE "db" SET balance = new_balance, lasttxid = self.txid WHERE snowflake = transaction["account"]"""
            query.update({'snowflake': transaction["account"]}, {
                           'balance': new_balance, 'lasttxid': self.txid}, "db")
        else:
            # Add staked amount to balance
            new_balance = float(
                result_set["balance"]) + float(transaction["amount"])

            # Get previous amount staked by user
            result_set = query.select(
                ["staked"], {'snowflake': transaction["account"]}, "db", "fetchone")

            # Add transaction amount to previous amount staked by user
            new_staked = float(result_set["staked"]) + \
                float(transaction["amount"])

            # Update user's balance with new information
            #"""UPDATE "db" SET balance = new_balance, lasttxid = self.txid WHERE snowflake = transaction["account"]"""
            query.update({'snowflake': transaction["account"]}, {'balance': new_balance, 'staked': new_staked,
                                                                   'lasttxid': self.txid}, "db")

        message = """{}: UPDATED; account: {},
        new balance: {}, amount: {}""".format(self.coin, transaction["account"], new_balance, transaction["amount"])
        output.success(message)
        return


if __name__ == "__main__":
    txid = str(sys.argv[1])
    config_path = os.getcwd()+"/walletnotify/walletnotify.json"
    config = parsing.parse_json(config_path)
    notify = Walletnotify()
    query = Query_db(config)

    # Get transaction information from wallet
    def gettransaction(config, txid):
        config_rpc = config["rpc"]
        rpc_host = config_rpc["rpc_host"]
        rpc_port = config_rpc["rpc_port"]
        rpc_credentials = (
            config_rpc["rpc_user"], config_rpc["rpc_pass"])
        serverURL = 'http://' + rpc_host + ':' + rpc_port
        headers = {'content-type': 'application/json'}
        payload = json.dumps(
            {"method": "gettransaction", "params": [txid], "jsonrpc": "2.0"})
        response = requests.get(serverURL, headers=headers, data=payload,
                                auth=(rpc_credentials))
        return response.json()['result']

    transactions = gettransaction(config, txid)
    notify.check_txs(config, txid, transactions)
