
CREATE TABLE reviews (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source VARCHAR(20) NOT NULL,
    review_id TEXT NOT NULL,
    review_date TIMESTAMPTZ NOT NULL,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT NOT NULL,
    title TEXT,
    content TEXT,
    app_version TEXT,
    app_version_source TEXT,
    country VARCHAR(2),
    helpful_votes INTEGER,
    vote_count INTEGER,
    developer_reply TEXT,
    developer_reply_date TIMESTAMPTZ,

    CONSTRAINT valid_source
        CHECK (source IN ('App Store', 'Google Play')),

    CONSTRAINT unique_source_review
        UNIQUE (source, review_id)
);

CREATE INDEX idx_reviews_date
    ON reviews (review_date);

CREATE INDEX idx_reviews_source_rating
    ON reviews (source, rating);
