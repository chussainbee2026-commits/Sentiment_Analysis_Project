

# --- Import required libraries ---
from flask import Flask, render_template, request, jsonify
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import re
import os
import json

# ============================================================
# Initialize Flask App
# ============================================================
app = Flask(__name__)

# ============================================================
# Initialize VADER Sentiment Analyzer
# VADER = Valence Aware Dictionary and sEntiment Reasoner
# It is a pretrained model specially built for social media,
# reviews, and short texts. No training required!
# ============================================================
vader_analyzer = SentimentIntensityAnalyzer()

# ============================================================
# Path to our Amazon Reviews dataset
# ============================================================
DATASET_PATH = os.path.join(os.path.dirname(__file__), "Amazon_Reviews.csv")


# ============================================================
# HELPER FUNCTION: Clean the review text
# Preprocessing = making text clean before analysis
# ============================================================
def clean_text(text):
    """
    Clean the review text by:
    - Removing extra spaces
    - Stripping leading/trailing whitespace
    We keep the text mostly original so the model
    can understand the sentiment naturally.
    """
    if not text or not isinstance(text, str):
        return ""
    # Remove multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text)
    # Strip leading and trailing whitespace
    text = text.strip()
    return text


# ============================================================
# HELPER FUNCTION: Analyze sentiment using VADER
# ============================================================
def analyze_with_vader(text):
    """
    VADER gives us 4 scores:
    - pos  → how positive the text is (0 to 1)
    - neg  → how negative the text is (0 to 1)
    - neu  → how neutral the text is  (0 to 1)
    - compound → overall score (-1 to +1)
      -1 = very negative, 0 = neutral, +1 = very positive

    Decision Rules:
    - compound >= 0.05  → POSITIVE
    - compound <= -0.05 → NEGATIVE
    - otherwise         → NEUTRAL
    """
    scores = vader_analyzer.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.05:
        label = "Positive"
        emoji = "😊"
        color = "positive"
    elif compound <= -0.05:
        label = "Negative"
        emoji = "😞"
        color = "negative"
    else:
        label = "Neutral"
        emoji = "😐"
        color = "neutral"

    return {
        "label": label,
        "emoji": emoji,
        "color": color,
        "compound_score": round(compound, 4),
        "positive_score": round(scores["pos"], 4),
        "negative_score": round(scores["neg"], 4),
        "neutral_score": round(scores["neu"], 4),
    }


# ============================================================
# HELPER FUNCTION: Analyze sentiment using TextBlob
# ============================================================
def analyze_with_textblob(text):
    """
    TextBlob gives us:
    - polarity    → ranges from -1 (negative) to +1 (positive)
    - subjectivity → 0 = objective, 1 = very subjective

    Decision Rules:
    - polarity > 0   → POSITIVE
    - polarity < 0   → NEGATIVE
    - polarity == 0  → NEUTRAL
    """
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

    if polarity > 0:
        label = "Positive"
        emoji = "😊"
        color = "positive"
    elif polarity < 0:
        label = "Negative"
        emoji = "😞"
        color = "negative"
    else:
        label = "Neutral"
        emoji = "😐"
        color = "neutral"

    return {
        "label": label,
        "emoji": emoji,
        "color": color,
        "polarity": round(polarity, 4),
        "subjectivity": round(subjectivity, 4),
    }


# ============================================================
# HELPER FUNCTION: Load dataset and compute statistics
# ============================================================
def load_dataset_stats():
    """
    Load the Amazon Reviews CSV and compute basic statistics.
    Returns a dictionary with counts and preview rows.
    """
    try:
        df = pd.read_csv(DATASET_PATH, nrows=500, on_bad_lines='skip')

        # Keep only the important columns
        df = df[["Rating", "Review Title", "Review Text"]].dropna()

        # Clean up rating text: "Rated 5 out of 5 stars" → 5
        def extract_rating(r):
            match = re.search(r'\d+', str(r))
            return int(match.group()) if match else None

        df["Stars"] = df["Rating"].apply(extract_rating)
        df = df.dropna(subset=["Stars"])
        df["Stars"] = df["Stars"].astype(int)

        # Count reviews per star rating
        rating_counts = df["Stars"].value_counts().sort_index().to_dict()

        # Preview: first 8 rows for the table
        preview = df[["Stars", "Review Title", "Review Text"]].head(8)
        preview_list = preview.to_dict(orient="records")

        # Truncate long review text for display
        for row in preview_list:
            if len(str(row["Review Text"])) > 150:
                row["Review Text"] = str(row["Review Text"])[:150] + "..."

        total = len(df)

        return {
            "total": total,
            "rating_counts": rating_counts,
            "preview": preview_list,
        }
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return {"total": 0, "rating_counts": {}, "preview": []}


# ============================================================
# ROUTE 1: Home Page
# URL: http://localhost:5000/
# ============================================================
@app.route("/")
def home():
    """
    Render the main home page.
    Also loads dataset statistics to display on the page.
    """
    stats = load_dataset_stats()
    return render_template("index.html", stats=stats)


# ============================================================
# ROUTE 2: Analyze Sentiment (API Endpoint)
# URL: http://localhost:5000/analyze
# Method: POST (sends data from the form)
# ============================================================
@app.route("/analyze", methods=["POST"])
def analyze():
    """
    This route receives review text from the frontend,
    runs both VADER and TextBlob analysis,
    and returns the results as JSON.
    """
    # Get the review text from the form submission
    review_text = request.form.get("review_text", "").strip()

    # Check if review text is empty
    if not review_text:
        return jsonify({"error": "Please enter a review to analyze."})

    # Step 1: Clean the text
    cleaned_text = clean_text(review_text)

    # Step 2: Analyze with VADER (primary model)
    vader_result = analyze_with_vader(cleaned_text)

    # Step 3: Analyze with TextBlob (secondary model)
    textblob_result = analyze_with_textblob(cleaned_text)

    # Step 4: Determine final/combined sentiment
    # We use VADER as the primary decision maker
    final_label = vader_result["label"]
    final_emoji = vader_result["emoji"]
    final_color = vader_result["color"]

    # Step 5: Build the response dictionary
    result = {
        "review_text": review_text[:300],     # Show first 300 chars
        "cleaned_text": cleaned_text[:300],
        "final_label": final_label,
        "final_emoji": final_emoji,
        "final_color": final_color,
        "vader": vader_result,
        "textblob": textblob_result,
    }

    return jsonify(result)


# ============================================================
# ROUTE 3: Bulk / Product Review Analysis
# URL: http://localhost:5000/analyze-bulk
# Method: POST (JSON body with list of reviews)
# ============================================================
@app.route("/analyze-bulk", methods=["POST"])
def analyze_bulk():
    """
    Accepts a JSON body: { "reviews": ["review1", "review2", ...] }
    Analyzes each review individually, then computes an overall
    aggregate sentiment for the whole product.
    """
    data    = request.get_json()
    reviews = data.get("reviews", [])

    if not reviews or len(reviews) < 2:
        return jsonify({"error": "Please provide at least 2 reviews."})

    results   = []  
    compounds = []   # collect VADER compound scores for averaging

    for review in reviews:
        cleaned  = clean_text(review)
        if not cleaned:
            continue
        vader_r  = analyze_with_vader(cleaned)
        compounds.append(vader_r["compound_score"])
        results.append({
            "text":  review,
            "label": vader_r["label"],
            "emoji": vader_r["emoji"],
            "color": vader_r["color"],
            "compound": vader_r["compound_score"],
        })

    if not results:
        return jsonify({"error": "No valid reviews found."})

    # Count how many are positive / negative / neutral
    count_pos = sum(1 for r in results if r["label"] == "Positive")
    count_neg = sum(1 for r in results if r["label"] == "Negative")
    count_neu = sum(1 for r in results if r["label"] == "Neutral")
    total     = len(results)

    # Percentage breakdown
    pct_pos = round(count_pos / total * 100, 1)
    pct_neg = round(count_neg / total * 100, 1)
    pct_neu = round(count_neu / total * 100, 1)

    # Average compound score → overall verdict
    avg_compound = round(sum(compounds) / len(compounds), 4)

    if avg_compound >= 0.05:
        overall_label = "Positive"
        overall_emoji = "😊"
        overall_color = "positive"
    elif avg_compound <= -0.05:
        overall_label = "Negative"
        overall_emoji = "😞"
        overall_color = "negative"
    else:
        overall_label = "Neutral"
        overall_emoji = "😐"
        overall_color = "neutral"

    # Human-friendly description
    overall_desc = (
        f"{pct_pos}% of reviewers liked it, "
        f"{pct_neg}% disliked it, "
        f"{pct_neu}% were neutral. "
        f"Average sentiment score: {avg_compound}."
    )

    return jsonify({
        "overall_label": overall_label,
        "overall_emoji": overall_emoji,
        "overall_color": overall_color,
        "overall_desc":  overall_desc,
        "avg_compound":  avg_compound,
        "total":     total,
        "count_pos": count_pos,
        "count_neg": count_neg,
        "count_neu": count_neu,
        "pct_pos":   pct_pos,
        "pct_neg":   pct_neg,
        "pct_neu":   pct_neu,
        "results":   results,
    })


# ============================================================
# ROUTE 4: Dataset Statistics (for charts)
# URL: http://localhost:5000/dataset-stats
# ============================================================
@app.route("/dataset-stats")
def dataset_stats():
    """
    Returns dataset statistics as JSON for the chart.
    """
    stats = load_dataset_stats()
    return jsonify(stats)


# ============================================================
# Run the Flask App
# Debug=True shows helpful error messages during development
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  Amazon Sentiment Analyzer is starting...")
    print("  Open your browser and go to:")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
