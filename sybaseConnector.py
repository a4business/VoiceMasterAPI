import os
import pyodbc
from dotenv import load_dotenv
import logging
import json
import re

class SybaseConnector:
    def __init__(self, env_path='.env.local', timeout=3):
        load_dotenv(env_path)
        self.conn = None
        self.connect(timeout=timeout)


    def connect(self, timeout=3):
        logging.basicConfig(
            filename='sybase_connector.log',
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='[ %Y-%m-%d %H:%M:%S ]'
        )
        try:
            self.conn = pyodbc.connect(
                f"DRIVER={os.getenv('SYBASE_DRIVER','FreeTDS')};"
                f"TDS_Version={os.getenv('SYBASE_TDS_VERSION', '5.0')};"
                f"SERVER={os.getenv('SYBASE_SERVER')};"
                f"PORT={os.getenv('SYBASE_PORT')};"
                f"DATABASE={os.getenv('SYBASE_DATABASE')};"
                f"UID={os.getenv('SYBASE_UID')};"
                f"PWD={os.getenv('SYBASE_PWD')};"
                f"Timeout={timeout};"
            )
        except Exception as e:
            error_msg = f"Connection error: {e}"
            logging.error(error_msg)
            self.conn = None
            raise ConnectionError(error_msg)

    def query(self, sql, params=None):
        if self.conn is None:
            self.connect()   
                 
        cursor = self.conn.cursor()
        logging.info(f"Query: {sql} | Params: {json.dumps(params or [])}")
        cursor.execute(sql, params or [])
        results = []
        while True:
            rows = []
            columns = [column[0] for column in cursor.description] if cursor.description else []
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                rows.append(row)
            if columns and rows:
                results.extend([dict(zip(columns, row)) for row in rows])
            if not cursor.nextset():
                break
        if self.conn:
            self.conn.commit()
        logging.info(f"Rows: {json.dumps(results, default=str)}")
        # Convert all values to strings, handle None as empty string for Json compatibility
        # results = [
        #     {col: f'{str(val)}' if val is not None else '' for col, val in zip(columns, row)}
        #     for row in cursor.fetchall()
        # ]
        cursor.close()
        self.close()
        return results
        
    def getUsers(self):
        return self.query("SELECT * FROM config_users")
        
    def getBalance(self, acctid, sip_login=None):
        accounts = self.getAccount(acctid, sip_login)
        return accounts[0]['balance'] if accounts else None
          
    def addAccount(self, sip_login, sip_password=None, web_login=None, web_password=None):
        if not sip_login:
            raise ValueError("sip_login is required")
        
        sip_password_val = sip_password if sip_password is not None else ''
        query = ( f"exec ifone..sp_account_add '{sip_login}', '{sip_password_val}', '', 'email@dot.com', '', '', 1000, '', 1000, '', 1, 'Company', 0, '0', '', '{sip_login}', 0, 0, 0, 0, 15, '', 112, '840', '', 1, 90, 0, '', '', 0"  )
        params = []

        try:
            result = self.query(query, params)          
            print(json.dumps(result, indent=2))
            system_message = None
            for row in result:
                for value in row.values():
                    if isinstance(value, str) and 'SYSTEM MESSAGE' in value:
                        system_message = value.replace('tempvar += "', '').replace('";', '')
                        self.close()    
                        return {"error": system_message}    
                        
                    if isinstance(value, str) and 'f_searchSubmit2(' in value:
                        match = re.search(r'f_searchSubmit2\((\d+)\)', value)
                        if match:
                            account_id = int(match.group(1))
                            return self.getAccount(account_id)
                            
                if system_message:
                    break
                                        
            return result if result else None
        
        
        except Exception as e:
            logging.error(f"Failed to add account: {e}")
            self.close()
            return False

    def getAccount(self, acctid=None, sip_login=None):
        sip_domain = os.getenv("SIP_DOMAIN", "")
        base_query = (
            "SELECT a.acctid as acctid, "
            "login as web_login, password as web_password, "
            "ISNULL(caller_id,login) as sip_login, "
            "ISNULL(akey, '') + '#' as sip_password, "
            "convert(varchar(100),b.credit - b.debit) as balance, "
            f"'{sip_domain}' as sip_domain "
            "FROM member m, authentication a, account b "
            "WHERE  m.acctid = a.acctid AND "
                "m.acctid = b.acctid AND "
                "m.acctid > 0"
        )
        params = []
        if acctid is not None:
            base_query += " AND m.acctid = ? "
            params.append(int(acctid))

        if sip_login is not None:
            base_query += " AND ISNULL(caller_id,login) = ? "
            params.append(sip_login)

        return self.query(base_query, params)
        

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

# Example usage:
# connector = SybaseConnector()
# results = connector.query("SELECT * FROM config_users")
# for row in results:
#     print(row)
# connector.close()
