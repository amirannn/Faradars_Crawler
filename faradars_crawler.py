import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from elasticsearch import Elasticsearch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


def es_init(index_name):
    es = Elasticsearch('http://localhost:9200')
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
    index_settings = {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 0
        },
        'mappings': {
            'properties': {
                'title': {'type': 'text'},
                'description': {'type': 'text'},
                'url': {'type': 'keyword'},
                'category': {'type': 'text'}
            }
        }
    }
    es.indices.create(index=index_name, body=index_settings)
    return es


def index_courses(es, index_name, category_url):
    response = requests.get(category_url)
    if response.status_code != 200:
        return []

    category_soup = BeautifulSoup(response.text, 'html.parser')
    course_anchors = category_soup.find_all('a', rel='bookmark')

    for anchor in course_anchors:
        course_url = urljoin(category_url, anchor['href'])
        course_title = anchor.get_text()
        category_title = get_category_title(anchor)
        course_description = get_course_description(anchor, course_url)
        document = {
            'title': course_title,
            'description': course_description,
            'url': course_url,
            'category': category_title,
        }
        es.index(index=index_name, body=document)



def get_category_title(anchor):
    category_title_tag = anchor.find_previous('a')
    return category_title_tag.get_text() if category_title_tag else 'Unknown category'


def get_course_description(anchor, course_url):
    description_tag = anchor.find_next('a')
    if description_tag and urljoin(URL, description_tag['href']) == course_url:
        return description_tag.get_text()
    return 'No description available'


def scroll_search(es, index_name, query, size=100, scroll='2m'):
    query_with_size = query.copy()
    query_with_size['size'] = size
    data = es.search(index=index_name, body=query_with_size, scroll=scroll)
    sid = data['_scroll_id']
    scroll_size = len(data['hits']['hits'])
    results = data['hits']['hits']

    while scroll_size > 0:
        data = es.scroll(scroll_id=sid, scroll=scroll)
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])
        results.extend(data['hits']['hits'])

        if len(results) >= 100:
            break

    return results[:100]


def train_model(courses):
    texts = [course['_source']['description'] for course in courses]
    categories = [course['_source']['category'] for course in courses]

    X_train, X_test, y_train, y_test = train_test_split(texts, categories, test_size=0.2, random_state=42)
    model = make_pipeline(TfidfVectorizer(), MultinomialNB())
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model accuracy: {accuracy}")

    return model


def predict_category(model, description):
    return model.predict([description])[0]





URL = 'https://blog.faradars.org/'
#راه اندازی الستیک
index_name = 'courses'
es = es_init(index_name)

#ایندکس کردن مقالات
custom_category_links = [
    'https://blog.faradars.org/category/programming/',
    'https://blog.faradars.org/category/english-language/',
    'https://blog.faradars.org/category/mathematics/',
    'https://blog.faradars.org/category/biology/',
    'https://blog.faradars.org/category/health/'
]
for category_url in custom_category_links:
    index_courses(es, index_name, category_url)

#بازیابی اطلاعات از ایندکس ها
query = {
    'query': {
        'match_all': {}
    }
}
courses = scroll_search(es, index_name, query)

#تمرین دادن مدل بیز
model = train_model(courses)

#پیش‌بینی از کتگوری و نوشتن در فایل
with open("predicted_categories.txt", "w", encoding="utf-8") as f:
    for course in courses:
        description = course['_source']['description']
        real_category = course['_source']['category']
        predicted_category = predict_category(model, description)
        is_correct = real_category == predicted_category
        f.write(f"Title: {course['_source']['title']}\n")
        f.write(f"URL: {course['_source']['url']}\n")
        f.write(f"Real Category: {real_category}\n")
        f.write(f"Predicted Category: {predicted_category}\n")
        f.write(f"Correct: {is_correct}\n\n")