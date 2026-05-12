import asyncio
import sqlite3
import sys
import os
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gamespy.gs_database import GamespyDatabase

async def run():
    try:
        print("Initializing RAM Disk DB")
        raw_db = GamespyDatabase(filename=":memory:")
        raw_db.initialize_database()
        
        print("Executing check_user_exists(9999, 'BATT')")
        print("Executing create_user()")
        profileid = raw_db.create_user(
            userid=9999, 
            password="my_secret_pass", 
            email="tester@gamespy.dev", 
            uniquenick="ProGamer", 
            gsbrcd="BATTE1", 
            firstname="Test", 
            lastname="User", 
            countrycode="US"
        )
        print(f"ProfileID Created: {profileid}")
        
    except Exception as e:
        print("EXCEPTION CAUGHT!")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
