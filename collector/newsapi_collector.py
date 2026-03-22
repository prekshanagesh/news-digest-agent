import requests
from app.config import NEWSAPI_KEY

def fetch_newsapi_articles(query:str,from_date:str,language:str='en',page_size:int=20)->list[dict]:
    url="https://newsapi.org/v2/everything"
    params={
        "q": query,
        "from": from_date,
        "language":language,
        "sortBy":"publishedAt",
        "pageSize":page_size,
        "apiKey":NEWSAPI_KEY
    }
    response=requests.get(url,params=params,timeout=30)
    response.raise_for_status()
    data=response.json()
    articles=[]
    for item in data.get("articles",[]):
        articles.append({
            "title":item.get("title","").strip(),
            "url":item.get("url","").strip(),
            "source":(item.get("source")or{}).get("name","").strip(),
            "published_at":item.get("publishedAt"),
            "summary":item.get("description","")or"",
            "raw_source_type":"newsapi",
        })
    return articles