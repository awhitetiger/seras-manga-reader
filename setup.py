import sqlite3
import os

def setup():
    conn = sqlite3.connect("manga.db")
    
    cursor = conn.cursor()  
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS manga (
        id INTEGER PRIMARY KEY,
        mangaid TEXT NOT NULL UNIQUE,
        json TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        mangaid TEXT,
        json TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    
    # Define the folder paths
    folders = ['./static', './static/mangacache']

    # Create the folders if they do not exist
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f'Created folder: {folder}')
        else:
            print(f'Folder already exists: {folder}')    
    
setup()