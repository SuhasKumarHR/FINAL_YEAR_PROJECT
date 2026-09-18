import csv
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsClassifier


class FailureClassifier:

    def __init__(self, dataset_path=None, n_neighbors=3):

        if dataset_path is None:
            dataset_path = Path(__file__).parent / "failure_dataset.csv"

        self.dataset_path = Path(dataset_path)

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2)
        )

        self.model = KNeighborsClassifier(
            n_neighbors=n_neighbors,
            weights="distance"
        )

        self._load_and_train()

    def _load_and_train(self):

        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {self.dataset_path}"
            )

        error_messages = []
        categories = []

        with open(
            self.dataset_path,
            "r",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                error_message = row["error_message"].strip()
                category = row["category"].strip()

                if error_message and category:
                    error_messages.append(error_message)
                    categories.append(category)

        if len(error_messages) < 3:
            raise ValueError(
                "Not enough training data for KNN."
            )

        X = self.vectorizer.fit_transform(error_messages)

        self.model.fit(X, categories)

        print(
            f"[SUCCESS] KNN trained with "
            f"{len(error_messages)} failure examples."
        )

    def classify(self, error_log):

        if not error_log:
            return "UNKNOWN"

        X = self.vectorizer.transform([error_log])

        prediction = self.model.predict(X)[0]

        return prediction

    def classify_with_confidence(self, error_log):

        if not error_log:
            return {
                "category": "UNKNOWN",
                "confidence": 0.0
            }

        X = self.vectorizer.transform([error_log])

        prediction = self.model.predict(X)[0]

        probabilities = self.model.predict_proba(X)[0]

        confidence = max(probabilities)

        return {
            "category": prediction,
            "confidence": round(float(confidence), 3)
        }