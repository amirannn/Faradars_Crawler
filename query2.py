from elasticsearch import Elasticsearch

# Connect to Elasticsearch
es = Elasticsearch("http://localhost:9200")

search_query = {
    "query": {
        "multi_match": {
            "query": "ریاضی",
            "fields": ["title^2" , "description"]
        }
    }
}

q1 = es.search(index="courses", body=search_query)

print(q1)