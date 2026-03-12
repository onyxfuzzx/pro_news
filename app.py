from flask import Flask, request, render_template, flash, redirect, url_for
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
import os
import requests
import markdown as md
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_classic.agents import initialize_agent, AgentType
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24).hex())

llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    api_key=os.getenv("GROQ_API_KEY"),
)

# Faster model for agent (fewer roundtrips matter more than model size)
agent_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
)
search_tool = DuckDuckGoSearchResults(num_results=3)

agent = initialize_agent(
    tools=[search_tool],
    llm=agent_llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False,
    handle_parsing_errors=True,
    max_iterations=3,
)


@app.template_filter('markdown')
def markdown_filter(text):
    """Convert Markdown text to HTML."""
    if text:
        return md.markdown(text)
    return text

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

                # --- Run summary/sentiment AND agent verification in PARALLEL ---
                def run_summary_sentiment():
                    combined_prompt = PromptTemplate.from_template("""
You are a smart news analyzer.
The user provides text extracted from a webpage.

TASK 1 - SUMMARY:
- First, check if the content looks like a news article (events, dates, places, people, etc.).
- If it is NOT news, reply with ONLY: "Not a valid news article." and stop.
- If it IS news:
    - Summarize it in clear bullet points (5–10 points, depending on article length).
    - Each point should cover one key fact or event.
    - Keep the summary simple, factual, and easy to read.
    - At the end, include:
        - Source: {url}
        - Author: {authors}

TASK 2 - SENTIMENT:
- Analyze the overall sentiment of the article.
- Return one of these: Positive, Neutral, or Negative.

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
===SUMMARY===
(your summary here)
===SENTIMENT===
(Positive, Neutral, or Negative)

Here is the article text:

{text}

Now, generate the response:
""")
                    chain = combined_prompt | llm
                    return chain.invoke({"text": text[:5000], "url": url, "authors": authors}).content

                def run_agent_verification():
                    prompt = f"""
You are a news verification assistant. Complete BOTH tasks below.

TASK 1 - AUTHENTICITY CHECK:
1. Use the duckduckgo_results_json tool to search for this news story.
2. Check if the news is reported by reliable sources.
3. Rate reliability as: "High", "Medium", or "Low".
4. Provide a brief 2-3 sentence explanation.

TASK 2 - RELATED ARTICLES:
1. From your search results, find 3-5 real articles covering the same story.

Article Title: {title}
Source URL: {url}
Article Text (truncated): {text[:1500]}

FORMAT YOUR FINAL ANSWER EXACTLY LIKE THIS:
===AUTHENTICITY===
(High/Medium/Low reliability with explanation)
===RELATED===
Source: [source name], URL: [article URL]
"""
                    return agent.run(prompt)

                # Run both in parallel with timeout
                with ThreadPoolExecutor(max_workers=2) as executor:
                    summary_future = executor.submit(run_summary_sentiment)
                    agent_future = executor.submit(run_agent_verification)

                    # Get summary (wait up to 30s)
                    try:
                        combined_result = summary_future.result(timeout=30)
                        if "===SUMMARY===" in combined_result and "===SENTIMENT===" in combined_result:
                            parts = combined_result.split("===SENTIMENT===")
                            summary = parts[0].replace("===SUMMARY===", "").strip()
                            sentiment = parts[1].strip()
                        else:
                            summary = combined_result.strip()
                            sentiment = "Unknown"
                    except Exception as e:
                        summary = f"Error generating summary: {str(e)}"
                        sentiment = "Unknown"

                    # Get agent results (wait up to 45s)
                    try:
                        combined_agent_result = agent_future.result(timeout=45)
                        if "===AUTHENTICITY===" in combined_agent_result and "===RELATED===" in combined_agent_result:
                            auth_part, related_part = combined_agent_result.split("===RELATED===", 1)
                            authenticity = auth_part.replace("===AUTHENTICITY===", "").strip()
                            related_articles = []
                            for line in related_part.strip().split("\n"):
                                line = line.strip()
                                if line and "Source:" in line and "URL:" in line:
                                    source_part, url_part = line.split("URL:", 1)
                                    source = source_part.replace("Source:", "").strip()
                                    article_url = url_part.strip()
                                    if article_url:
                                        related_articles.append({"source": source, "url": article_url})
                            related_articles = related_articles[:5]
                        else:
                            authenticity = combined_agent_result.strip()
                            related_articles = []
                    except FuturesTimeout:
                        authenticity = "Timed out — try again"
                        related_articles = []
                    except Exception as e:
                        authenticity = f"Error: {str(e)}"
                        related_articles = []

            except requests.exceptions.RequestException as e:
                summary = f"Error: Could not fetch the webpage. Please check the URL. ({str(e)})"
            except Exception as e:
                summary = f"Error processing the webpage: {str(e)}"

    # Parse sentiment class for template
    sentiment_class = "unknown"
    if sentiment:
        s = sentiment.strip().lower()
        if "positive" in s:
            sentiment_class = "positive"
        elif "negative" in s:
            sentiment_class = "negative"
        elif "neutral" in s:
            sentiment_class = "neutral"

    # Parse authenticity level and explanation for template
    auth_level = "unknown"
    auth_level_display = "N/A"
    auth_explanation = ""
    if authenticity:
        auth_lower = authenticity.lower()
        if "high" in auth_lower:
            auth_level = "high"
            auth_level_display = "High"
        elif "medium" in auth_lower:
            auth_level = "medium"
            auth_level_display = "Medium"
        elif "low" in auth_lower:
            auth_level = "low"
            auth_level_display = "Low"
        else:
            auth_level_display = "Checked"
        auth_explanation = authenticity

    # Render template
    return render_template('index.html',
                           title=title,
                           authors=authors,
                           publish_date=publish_date,
                           top_image=top_image,
                           summary=summary,
                           sentiment=sentiment,
                           sentiment_class=sentiment_class,
                           authenticity=authenticity,
                           auth_level=auth_level,
                           auth_level_display=auth_level_display,
                           auth_explanation=auth_explanation,
                           url=url,
                           related_articles=related_articles)


if __name__ == '__main__':
    app.run(debug=True)