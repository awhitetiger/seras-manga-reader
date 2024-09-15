from flask import Flask, render_template, jsonify, request, redirect, url_for
from mangadata import *
from setup import *
import os
import re

app = Flask(__name__)

def get_sorted_images(folder_path):
    # Regular expression to match the filenames and extract the number
    pattern = re.compile(r'(\d+)-.*\.(jpg|jpeg|png|gif)$', re.IGNORECASE)
    
    # List to store image filenames
    image_files = []

    # Iterate through the files in the folder
    for filename in os.listdir(folder_path):
        match = pattern.search(filename)
        if match:
            number = int(match.group(1))
            image_files.append((number, filename))

    # Sort the list of tuples by the number
    image_files.sort(key=lambda x: x[0])

    # Return just the filenames in sorted order
    return [filename for _, filename in image_files]

@app.route('/')
def index():
    addedManga = os.path.join(app.root_path, 'static')
    folders = [f for f in os.listdir(addedManga) if os.path.isdir(os.path.join(addedManga, f))]
    folders.remove("mangacache")
    if folders:
        sortedSeries = []
        for folder in folders:
            series = {
                "name": seriesTitle(folder),
                "id": folder
            }
            sortedSeries.append(series)
        return render_template('index.html', sortedSeries=sortedSeries)    
    else:
        return render_template('index_none.html')
        
@app.route('/search/', methods=['GET'])
def search():
    search = request.args.get('search', '')  # Get the search term from the query string
    if not search:
        return render_template("search_base.html")  # Redirect to the home page if no search term
    searchResults = searchManga(search, ["en"])  # Fetch all results
    page = request.args.get('page', 1, type=int)  # Get the current page, default to 1
    per_page = 9  # Number of results per page
    total_results = len(searchResults)  # Total number of results
    paginated_results = searchResults[(page - 1) * per_page: page * per_page]  # Get results for the current page

    return render_template(
        'search.html',
        search=search,
        results=paginated_results,
        page=page,
        per_page=per_page,
        total_results=total_results
    )
    
@app.route('/manga/<string:mangaid>')
def manga(mangaid):
    seriesInfo = getAddedSeries(mangaid)
    return render_template('info.html', seriesInfo=seriesInfo, mangaid=mangaid)

@app.route('/chapter/<string:mangaid>/<string:chapterid>/<int:page>')
def chapter(mangaid, chapterid, page):
    downloadChapter(chapterid, mangaid)
    nextchapter = nextChapter(mangaid, chapterid)
    pages = get_sorted_images(f"./static/{mangaid}/{chapterid}")
    return render_template("read.html", image=pages[page], mangaid=mangaid, chapterid=chapterid, page=page, numpages=len(pages), nextchapter=nextchapter)

@app.route('/add', methods=['GET'])
def addManga():
    mangaID = request.args.get('id', '')
    addSeries(mangaID, ["en"])
    return redirect(url_for('manga', mangaid=mangaID))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8078)
