from flask import Flask, render_template, request, session, send_file
import fitz  # PyMuPDF
from textblob import TextBlob
from langdetect import detect
from translate import Translator
import nltk
import os
import io

# 🔧 Force NLTK to look in the local project tokenizer folder first
nltk.data.path.insert(0, os.path.join(os.path.dirname(_file_), 'tokenizers'))

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

# Flask app setup
app = Flask(_name_)
app.secret_key = 'siddhi-secret-key'

# Upload folder
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

                # Extract text
                text = extract_text(filepath)

                # Detect language
                try:
                    lang = detect(text)
                except:
                    lang = 'unknown'

                # Process
                words = word_tokenize(text)
                words = [w.lower() for w in words if w.isalpha()]
                stop_words = set(stopwords.words("english"))
                filtered = [w for w in words if w not in stop_words]
                word_count = len(filtered)
                freq = nltk.FreqDist(filtered)
                top_keywords = freq.most_common(10)

                # Summarize
                sentences = sent_tokenize(text)
                summary = " ".join(sentences[:3]) if len(sentences) >= 3 else text

                # Translate summary if needed
                if lang != 'en':
                    try:
                        translator = Translator(to_lang="en", from_lang=lang)
                        summary = translator.translate(summary)
                    except:
                        summary += "\n(Note: Translation failed.)"

                # Sentiment
                sentiment_score = TextBlob(text).sentiment.polarity
                sentiment_result = (
                    "Positive" if sentiment_score > 0 else
                    "Negative" if sentiment_score < 0 else
                    "Neutral"
                )

                # Store each summary
                all_summaries.append(f"{file.filename}:\n{summary}\n\n")

                results.append({
                    "filename": file.filename,
                    "language": lang,
                    "word_count": word_count,
                    "top_keywords": top_keywords,
                    "summary": summary,
                    "sentiment": sentiment_result
                })

        # Save all summaries to session
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

if _name_ == "_main_":
    app.run(debug=True)