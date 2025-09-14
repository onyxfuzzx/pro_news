from flask import Flask, request, render_template, flash, redirect, url_for
import nltk
from textblob import TextBlob
from newspaper import Article, Config
from datetime import datetime
from urllib.parse import urlparse
import validators

nltk.download('punkt')

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

def get_website_name(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']

        if not validators.url(url):
            flash('Please enter a structurally valid URL.')
            return redirect(url_for('index'))
        
        try:
            config = Config()
            config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            config.request_timeout = 10

            article = Article(url, config=config)
            
            article.download()
            article.parse()
            
            title = article.title
            authors = ', '.join(article.authors)
            publish_date = article.publish_date.strftime('%B %d, %Y') if article.publish_date else "N/A"
            top_image = article.top_image

            if not authors:
                authors = get_website_name(url)

            article_text = article.text
            sentences = article_text.split('.')
            max_summarized_sentences = 5
            summary = '.'.join(sentences[:max_summarized_sentences]) + '.'
            
            if len(summary) <= 1 or not article_text:
                flash('Could not summarize this article. The content may be blocked or in an unreadable format.')
                return redirect(url_for('index'))

            analysis = TextBlob(article.text)
            polarity = analysis.sentiment.polarity

            if polarity > 0.1:
                sentiment = 'Positive 😊'
            elif polarity < -0.1:
                sentiment = 'Negative 😟'
            else:
                sentiment = 'Neutral 😐'
            
            return render_template('index.html', title=title, authors=authors, publish_date=publish_date, summary=summary, top_image=top_image, sentiment=sentiment, url=url)

        except Exception as e:
            flash(f'Failed to process the article. The website may be blocking automated scrapers. (Error: {e})')
            return redirect(url_for('index'))

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)

