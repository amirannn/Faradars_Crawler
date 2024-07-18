from elasticsearch import Elasticsearch

# Connect to Elasticsearch
es = Elasticsearch("http://localhost:9200")

search_query = {
    "query": {
        "match": {
            "category": "زیست",
        }
    }
}

q1 = es.search(index="courses", body=search_query)

print(q1)