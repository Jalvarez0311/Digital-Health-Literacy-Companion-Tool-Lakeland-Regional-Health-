import os
import mysql.connector
#import chatbot

#placeholders for all the connectors
mydb = mysql.connector.connect(
 host = 'placeholder',
 user = 'placeholder',
 password = 'placehodler',
 port = 'placeholder',
 database = 'placeholder'   
)

#get data
query = "SELECT * FROM patient_name;" #subject to change once the database is made available
cursor = mydb.cursor()
cursor.execute(query)

#this is where the information will be sent to the AI database
#Note, I have no Idea how it will work, this is just a placeholder
chatbot.attach(cursor.fetchall())
chatbot.ask("Create Discharge papers for the patient...") #query to be increased/tweaked later
