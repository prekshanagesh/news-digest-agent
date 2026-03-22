def build_digest_plan() -> dict:
    return {
        "target_topics": ["AI", "Politics", "World", "Technology", "Business", "Science", "Health", "Sports"],
        "min_articles_per_topic": 1,
        "max_articles_per_topic": 2,
        "max_final_articles": 5,  # was 10
        "fallback_queries": {
            "AI": "artificial intelligence OR llm OR openai OR model release",
            "Politics": "Trump OR election OR white house OR senate",
            "World": "war OR diplomacy OR india OR europe OR middle east",
            "Technology": "technology OR software OR chip OR startup",
            "Business": "economy OR stock market OR fed OR earnings OR inflation",
            "Science": "nasa OR space OR climate OR research OR discovery",
            "Health": "health OR medicine OR FDA OR disease OR mental health",
            "Sports": "NBA OR NFL OR football OR cricket OR tennis"
        }
    }