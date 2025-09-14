from flask import Flask, request, render_template, flash, redirect, url_for
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)
app.secret_key = 'your_super_secret_key'


llm =ChatGoogleGenerativeAI(model="gemini-2.0-flash")


@app.route('/', methods=['GET', 'POST'])
def index():
    summary = None    

    if request.method == 'POST':
        url = request.form['url'].strip()

        
        if not url:
            return render_template('index.html', summary="Please enter a URL.")
        elif not url.startswith("http://") and not url.startswith("https://"):
            return render_template('index.html', summary="Invalid URL. Must start with http:// or https://")
        elif len(url) < 10:
            return render_template('index.html', summary="Invalid URL. Too short.")

        try:
           
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            
            paragraphs = soup.find_all("p")
            text = " ".join([p.get_text() for p in paragraphs])

            
            author = "Unknown"

            
            meta_author = soup.find("meta", attrs={"name": "author"})
            if meta_author and meta_author.get("content"):
                author = meta_author["content"]

            
            if author == "Unknown":
                author_tag = soup.find(["span", "div"], class_=lambda x: x and "author" in x.lower())
                if author_tag:
                    author = author_tag.get_text().strip()

             
            if author == "Unknown":
                for p in paragraphs[:5]:   
                    text_p = p.get_text()
                    if text_p.lower().startswith("by "):
                        author = text_p[3:].strip()
                        break

            
            prompt = PromptTemplate.from_template(
                """
You are a smart news summarizer. 
The user provides text extracted from a webpage.

Rules:
- First, check if the content looks like a news article (events, dates, places, people, etc.).
- If it is NOT news, reply: "Not a valid news article."
- You do NOT need to visit the URL yourself. Use only the text provided.
- If it IS news:
    - Summarize it in clear bullet points (5–10 points, depending on article length).
    - Each point should cover one key fact or event.
    - Keep the summary simple, factual, and easy to read.
    - At the end, include:
        - Source: {url}
        - Author: {author}

Here is the article text:

{text}

Now, generate the response:
"""
            )

            chain = prompt | llm
            summary = chain.invoke({"text": text[:5000], "url": url, "author": author}).content   

        except requests.exceptions.RequestException:
            summary = "Error: Could not fetch the webpage. Please check the URL."

    return render_template('index.html', summary=summary)


if __name__ == '__main__':
    app.run(debug=True)

