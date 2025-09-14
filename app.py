from flask import Flask, request, render_template, flash, redirect, url_for
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.tools import DuckDuckGoSearchResults
from langchain.agents import initialize_agent, AgentType
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
search_tool = DuckDuckGoSearchResults(k=3) 


agent = initialize_agent(
    tools=[search_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False,
)

@app.route('/', methods=['GET', 'POST'])
def index():
    # Initialize all variables
    title = ""
    authors = "Unknown"
    publish_date = "Unknown"
    top_image = ""
    summary = None
    sentiment = None
    url = ""
    text = ""
    authenticity = None
    related_articles = []

    if request.method == 'POST':
        url = request.form['url'].strip()

        # Simple URL validation
        if not url:
            summary = "Please enter a URL."
        elif not url.startswith("http://") and not url.startswith("https://"):
            summary = "Invalid URL. Must start with http:// or https://"
        elif len(url) < 10:
            summary = "Invalid URL. Too short"
        else:
            try:
                response = requests.get(url, timeout=10)
                soup = BeautifulSoup(response.text, "html.parser")

                # Extract text paragraphs
                paragraphs = soup.find_all("p")
                text = " ".join([p.get_text() for p in paragraphs])

                # Extract title
                if soup.title:
                    title = soup.title.string.strip()

                # Extract author
                meta_author = soup.find("meta", attrs={"name": "author"})
                if meta_author and meta_author.get("content"):
                    authors = meta_author["content"]

                if authors == "Unknown":
                    author_tag = soup.find(["span", "div"], class_=lambda x: x and "author" in x.lower())
                    if author_tag:
                        authors = author_tag.get_text().strip()

                if authors == "Unknown":
                    for p in paragraphs[:5]:
                        text_p = p.get_text()
                        if text_p.lower().startswith("by "):
                            authors = text_p[3:].strip()
                            break

                # Extract publish date
                meta_date = soup.find("meta", attrs={"name": "date"})
                if meta_date and meta_date.get("content"):
                    publish_date = meta_date["content"]

                # Extract top image
                meta_image = soup.find("meta", attrs={"property": "og:image"})
                if meta_image and meta_image.get("content"):
                    top_image = meta_image["content"]

                # --- Summarize using LLM ---
                summary_prompt = PromptTemplate.from_template("""
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
        - Author: {authors}

Here is the article text:

{text}

Now, generate the response:
""")

                summary_chain = summary_prompt | llm
                summary = summary_chain.invoke({"text": text[:5000], "url": url, "authors": authors}).content

                # --- Sentiment Analysis ---
                sentiment_prompt = PromptTemplate.from_template("""
You are a sentiment analyzer. 
The user provides text extracted from a news article.

Rules:
- Analyze the overall sentiment of the article.
- Return one of these: Positive, Neutral, Negative.
- Keep it short, clear, and factual.

Here is the text:

{text}

Now, provide the sentiment:
""")
                sentiment_chain = sentiment_prompt | llm
                sentiment = sentiment_chain.invoke({"text": text[:5000]}).content
                print(sentiment)

                # --- Authenticity Chain with error handling ---
                try:
 
                    auth_prompt = f"""
                    You are a news authenticity checker. 

                    Steps:
                    1. Use a web search tool (like DuckDuckGo) to find information about this news article.
                    2. Verify if the news is reported by reliable sources.
                    3. Based on the findings, determine the authenticity of the article.

                    Article Details:
                    - Source URL: {url}
                    - Article Text (truncated to 2000 chars): {text[:2000]}

                    Instructions:
                    - Return a short answer: "High", "Medium", or "Low" reliability.
                    - Provide a brief 5 to 10 sentence explanation for your rating.
                    - Only base your assessment on real sources found via web search, do not hallucinate.
                    """

                    authenticity_result = agent.run(auth_prompt) 
                    authenticity = authenticity_result
                     
                except Exception as e:
                    authenticity = f"Error checking authenticity: {str(e)}"

                try:
 
                    related_prompt = f"""
                    You are a news assistant. Your task is to find 3–5 **real, reliable news articles** that cover the same story as the given article text.

                    Steps:
                    1. Use a web search tool (like DuckDuckGo) to search for the news story described in the text.
                    2. Only include articles that are clearly about the same events described in the text.
                    3. Use major reputable sources (CNN, NYTimes, Reuters, AP, Fox News, BBC).

                    Output format:
                    Return one article per line in this exact format:
                    Source: [source name], URL: [article URL]

                    Article Text:
                    {text}

                    Response:
                    """
                    
                    related_result = agent.run(related_prompt)
                    
                    related_articles = []
                    for line in related_result.split("\n"):
                        line = line.strip()
                        if line and "Source:" in line and "URL:" in line:
                            source_part, url_part = line.split("URL:", 1)
                            source = source_part.replace("Source:", "").strip()
                            url = url_part.strip()
                            if url: 
                                related_articles.append({"source": source, "url": url})

                    # Keep only the first 5
                    related_articles = related_articles[:5]
                    print(sentiment)
                    
                except Exception as e:
                    related_articles = [f"Error finding related articles: {str(e)}"]

            except requests.exceptions.RequestException as e:
                summary = f"Error: Could not fetch the webpage. Please check the URL. ({str(e)})"
            except Exception as e:
                summary = f"Error processing the webpage: {str(e)}"

    # Render template
    return render_template('index.html',
                           title=title,
                           authors=authors,
                           publish_date=publish_date,
                           top_image=top_image,
                           summary=summary,
                           sentiment=sentiment,
                           authenticity=authenticity,
                           related_articles=related_articles)


if __name__ == '__main__':
    app.run(debug=True)