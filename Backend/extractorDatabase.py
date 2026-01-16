import os
#import chatbot
import psycopg2

# Adding imports for supabase for DB connection
from dotenv import load_dotenv



# Fetch variables from .env
load_dotenv()
USER: str = os.getenv("user")
PASSWORD: str = os.getenv("password")
HOST: str = os.getenv("host")
PORT: str = os.getenv("port")
DBNAME: str = os.getenv("dbname")

# Check for .env files
if not (USER or PASSWORD or HOST or PORT or DBNAME):
    raise ValueError("Environment files not populated. Please setup your environment variables with a .env file.")

# Connect to the database
try:
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )
    print("Connection successful!")

    # Create a cursor to execute SQL queries
    cursor = connection.cursor()

    # Example query
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print("Current Time:", result)

    # Close the cursor and connection
    cursor.close()
    connection.close()
    print("Connection closed.")

except Exception as e:
    print(f"Failed to connect: {e}")

#this is where the information will be sent to the AI database
#Note, I have no Idea how it will work, this is just a placeholder
# chatbot.attach(cursor.fetchall())
# chatbot.ask("Create Discharge papers for the patient...") #query to be increased/tweaked later
