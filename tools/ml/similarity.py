"""
tools/ml/similarity.py
TF-IDF cosine similarity across claim variants.
High similarity across variants = AI-generated near-duplicates = fabrication signal.
"""
from typing import List, Tuple


def compute_variant_similarity(texts: List[str]) -> Tuple[float, List[str]]:
    """
    Compute mean pairwise TF-IDF cosine similarity across variant texts.

    Returns:
        (score, flags) where score 1.0 = near-identical (AI-generated),
        0.0 = organically diverse variants.
    """
    if len(texts) < 2:
        return 0.0, []

    flags: List[str] = []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=2000,
            sublinear_tf=True,
            stop_words="english",
        )
        tfidf_matrix = vectorizer.fit_transform(texts)
        sim_matrix = cosine_similarity(tfidf_matrix)

        # Upper triangle (excluding diagonal)
        n = sim_matrix.shape[0]
        upper_vals = [
            sim_matrix[i, j]
            for i in range(n)
            for j in range(i + 1, n)
        ]
        mean_sim = float(np.mean(upper_vals)) if upper_vals else 0.0
        max_sim = float(np.max(upper_vals)) if upper_vals else 0.0

        if max_sim > 0.85:
            flags.append(
                f"Near-identical variants detected (max sim={max_sim:.2f}) — "
                "AI-generated near-duplicates across platforms"
            )
        elif mean_sim > 0.70:
            flags.append(
                f"High variant similarity (mean={mean_sim:.2f}) — "
                "possible coordinated amplification using shared template"
            )

        return round(mean_sim, 3), flags

    except ImportError:
        return 0.5, ["sklearn unavailable — TF-IDF similarity not computed"]
    except Exception as e:
        return 0.5, [f"Similarity computation error: {e}"]
