from flask import Flask, render_template, request, session, send_file
import fitz  # PyMuPDF
from textblob import TextBlob
from langdetect import detect
from translate import Translator
import nltk
import os
import io

# Download required NLTK data on startup (safe for Render)
# nltk.download('punkt')
# nltk.download('stopwords')

# ✅ Corrected line
nltk.data.path.insert(0, os.path.join(os.path.dirname(__file__), 'tokenizers'))

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

app = Flask(__name__)
app.secret_key = 'siddhi-secret-key'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    results = []

    if request.method == "POST":
        files = request.files.getlist("pdfs")
        all_summaries = []

        for file in files:
            if file and file.filename.endswith(".pdf"):
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)

                text = extract_text(filepath)

                try:
                    lang = detect(text)
                except:
                    lang = 'unknown'

                words = word_tokenize(text)
                words = [w.lower() for w in words if w.isalpha()]
                stop_words = set(stopwords.words("english"))
                filtered = [w for w in words if w not in stop_words]
                word_count = len(filtered)
                freq = nltk.FreqDist(filtered)
                top_keywords = freq.most_common(10)

                sentences = sent_tokenize(text)
                summary = " ".join(sentences[:3]) if len(sentences) >= 3 else text

                if lang != 'en':
                    try:
                        translator = Translator(to_lang="en", from_lang=lang)
                        summary = translator.translate(summary)
                    except Exception as e:
                        summary += f"\n(Note: Translation failed: {e})"

                sentiment_score = TextBlob(text).sentiment.polarity
                sentiment_result = (
                    "Positive" if sentiment_score > 0 else
                    "Negative" if sentiment_score < 0 else
                    "Neutral"
                )

                all_summaries.append(f"{file.filename}:\n{summary}\n\n")

                results.append({
                    "filename": file.filename,
                    "language": lang,
                    "word_count": word_count,
                    "top_keywords": top_keywords,
                    "summary": summary,
                    "sentiment": sentiment_result
                })

        session['all_summaries'] = "\n".join(all_summaries)

    return render_template("index.html", results=results)

@app.route('/download_summary')
def download_summary():
    summary = session.get('all_summaries', '')
    if summary:
        buffer = io.BytesIO()
        buffer.write(summary.encode('utf-8'))
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name='summaries.txt',
            mimetype='text/plain'
        )
    return "No summary available for download"

def extract_text(path):
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)

if __name__ == "__main__":
    app.run(debug=True)
