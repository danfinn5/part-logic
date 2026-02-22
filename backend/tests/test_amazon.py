"""Tests for Amazon connector relevance filtering."""

from app.ingestion.amazon import AmazonConnector


class TestIsRelevant:
    def test_matching_title(self):
        """Title containing all query keywords is relevant."""
        assert AmazonConnector._is_relevant("Porsche 944 Engine Mount Replacement", "Porsche 944 engine mount")

    def test_non_matching_title(self):
        """Title with no query keyword overlap is not relevant."""
        assert not AmazonConnector._is_relevant("Whirlpool Refrigerator Ice Maker", "Porsche 944 engine mount")

    def test_partial_match_above_threshold(self):
        """Title matching enough significant keywords passes."""
        # "engine" and "mount" match (2/3 significant words: porsche, engine, mount)
        assert AmazonConnector._is_relevant("Engine Mount Bracket Heavy Duty", "Porsche engine mount")

    def test_partial_match_below_threshold(self):
        """Title matching too few significant keywords fails."""
        # Only "mount" matches (1/3 = 33%, but "dog" "food" are significant)
        assert not AmazonConnector._is_relevant("Dog Food Bowl Mount", "Porsche 944 engine mount")

    def test_stopwords_ignored(self):
        """Stopwords in the query don't count toward the match ratio."""
        # Query "for the car" → significant word is just "car"
        assert AmazonConnector._is_relevant("Car Parts Store", "for the car")
        assert not AmazonConnector._is_relevant("Dog Food Bowl", "for the car")

    def test_empty_query_passes(self):
        """Empty or all-stopword query passes everything through."""
        assert AmazonConnector._is_relevant("Anything Goes", "for the")

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        assert AmazonConnector._is_relevant("PORSCHE 944 ENGINE MOUNT", "porsche 944 engine mount")
