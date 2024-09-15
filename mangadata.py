import requests
import json
import time
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

base_url = "https://api.mangadex.org"

def seriesExists(id):
    conn = sqlite3.connect("manga.db")
    cursor = conn.cursor()  
    cursor.execute("SELECT * FROM manga WHERE mangaid = ? LIMIT 1", (id,))
    results = cursor.fetchone()
    if not results:
        conn.close()
        return False
    else:
        conn.close()
        return True

def getChapters(id, lang):
    
    i = 0
    chapterData = []
    
    while True:
        if (i == 0):
            r = requests.get(
                f"{base_url}/manga/{id}/feed",
                params={"translatedLanguage[]":lang,"limit":"500"},
            )
        else:
            offset = 500*i
            offset = str(offset)
            r = requests.get(
                f"{base_url}/manga/{id}/feed",
                params={"translatedLanguage[]":lang,"limit":"500","offset":offset},
            )            
        data = r.json()["data"]
        chapters = len(data)
        if (chapters == 0):
            break;
        chapterData += data
        time.sleep(1)
        print(chapters)
        i+=1

    sorted_chapters = sorted(chapterData, key=lambda x: float(x['attributes']['chapter']))
    
    seen_chapters = set()
    unique_data = []
    for item in sorted_chapters:
        chapter = item['attributes']['chapter']
        if chapter not in seen_chapters:
            seen_chapters.add(chapter)
            unique_data.append(item)

    return unique_data

def getSeriesInfoSearch(id, lang):
    seriesData = {
        "title": "",
        "altTitles": [],
        "descriptions": [],
        "chapters": [],
        "cover": "",
        "id": ""
    }
    
    # Define the directory to save images
    cache_dir = './static/mangacache/'
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    r = requests.get(
        f"{base_url}/manga/{id}?includes[]=author&includes[]=artist&includes[]=cover_art"
    )
    data = r.json()["data"]
    attributes = data["attributes"]
    relationships = data["relationships"]
    
    # Set title
    if "en" in attributes["title"]:
        seriesData["title"] = attributes["title"]["en"]
    else:   
        seriesData["title"] = attributes["title"]["ja-ro"]
    
    # Process cover art
    for rtype in relationships:
        if rtype["type"] == "cover_art":
            cover_url = f"https://uploads.mangadex.org/covers/{id}/" + rtype["attributes"]["fileName"] + ".256.jpg"
            seriesData["cover"] = cover_url
            
            # Download and save cover image
            cover_response = requests.get(cover_url)
            if cover_response.status_code == 200:
                cover_path = os.path.join(cache_dir, rtype["attributes"]["fileName"] + ".256.jpg")
                with open(cover_path, 'wb') as f:
                    f.write(cover_response.content)
                seriesData["cover"] = cover_path  # Update seriesData to point to the local file
            break
    
    # Set ID
    seriesData["id"] = id
    return seriesData

def getSeriesInfo(id, lang):
    seriesData = {
        "title": "",
        "altTitles": [],
        "descriptions": [],
        "chapters": [],
        "cover": ""
    }
    
    r = requests.get(
        f"{base_url}/manga/{id}?includes[]=author&includes[]=artist&includes[]=cover_art"
    )
    if "en" in r.json()["data"]["attributes"]["title"]:
        seriesData["title"] = r.json()["data"]["attributes"]["title"]["en"]    
    else:   
        seriesData["title"] = r.json()["data"]["attributes"]["title"]["ja-ro"]
    seriesData["altTitles"] = r.json()["data"]["attributes"]["altTitles"]
    seriesData["descriptions"] = r.json()["data"]["attributes"]["description"]
    seriesData["chapters"] = getChapters(id, lang)
    for rtype in r.json()["data"]["relationships"]:
        if rtype["type"] == "cover_art":
            seriesData["cover"] = rtype["attributes"]["fileName"]
            break
    return seriesData

def addSeries(id, lang):
    cover_base = "https://uploads.mangadex.org/covers"
    manga_folder = f"./static/{id}"
    seriesData = getSeriesInfo(id, lang)
    if not seriesExists(id):
        conn = sqlite3.connect("manga.db")
        cursor = conn.cursor()  
        cursor.execute("INSERT INTO manga (mangaid, json) VALUES (?, ?)", (id, json.dumps(seriesData)));
        conn.commit()
        conn.close()
        
        os.makedirs(manga_folder)
        cover = requests.get(f"{cover_base}/{id}/{seriesData['cover']}")
        filename = f"{manga_folder}/cover.png"
        with open(filename, "wb") as file:
            file.write(cover.content)

def getAddedSeries(id):
    conn = sqlite3.connect("manga.db")
    cursor = conn.cursor()  
    cursor.execute("SELECT * FROM manga WHERE mangaid = ? LIMIT 1", (id,))
    results = cursor.fetchone()
    seriesInfo = json.loads(results[2])
    return seriesInfo

def seriesTitle(id):
    info = getAddedSeries(id)
    return info["title"]
    
def seriesChapters(id):
    info = getAddedSeries(id)
    return info["chapters"]
    
def nextChapter(id, chapterid):
    chapters = seriesChapters(id)
    curChapterIndex = None

    # Find the index of the current chapter
    for index, chapter in enumerate(chapters):
        if chapter["id"] == chapterid:
            curChapterIndex = index
            break

    # Check if the current chapter was found and if there is a next chapter
    if curChapterIndex is not None and curChapterIndex < len(chapters) - 1:
        nextChapter = chapters[curChapterIndex + 1]
        return nextChapter["id"]
    else:
        return None  # No next chapter found or invalid current chapter

def download_page(chapter_folder, page_base, chapter_hash, page):
    response = requests.get(f"{page_base}/{chapter_hash}/{page}")
    filename = f"{chapter_folder}/{os.path.basename(page)}"
    with open(filename, "wb") as file:
        file.write(response.content)

def searchManga(title, lang):
    searchResults = []
    base_url = "https://api.mangadex.org"

    r = requests.get(
        f"{base_url}/manga",
        params={"title": title}
    )

    for manga in r.json()["data"]:
        thisManga = manga["id"]
        if os.path.exists(f"./static/mangacache/{thisManga}.json"):
            with open(f"./static/mangacache/{thisManga}.json", "r") as file:
                mangaInfo = json.loads(file.read())
                searchResults += [mangaInfo]
        else:
            mangaInfo = getSeriesInfoSearch(thisManga, lang)
            searchResults += [mangaInfo]
            with open(f"./static/mangacache/{thisManga}.json", "w") as file:
                file.write(json.dumps(mangaInfo))    

    return searchResults

    

def downloadChapter(id, mangaid):
    athome_base = "https://api.mangadex.org/at-home/server"
    page_base = "https://uploads.mangadex.org/data"
    manga_folder = f"./static/{mangaid}"
    chapter_folder = f"{manga_folder}/{id}"
    
    if os.path.exists(f"{chapter_folder}/download.txt"):
        return True  
    
    r = requests.get(f"{athome_base}/{id}")
    chapterData = r.json()['chapter']
    
    if not os.path.exists(manga_folder):
        os.makedirs(manga_folder)
    if not os.path.exists(chapter_folder):
        os.makedirs(chapter_folder)
    
    chapter_hash = chapterData['hash']
    pages = chapterData['data']

    max_workers = 20  # Adjust this based on system resources and API rate limits
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(download_page, chapter_folder, page_base, chapter_hash, page)
            for page in pages
        ]
        for future in as_completed(futures):
            future.result()  # Ensure all pages are downloaded
    
    # Write the completion file
    finishedFile = f"{chapter_folder}/download.txt"
    with open(finishedFile, "w") as file:
        file.write("a")
    
    return True