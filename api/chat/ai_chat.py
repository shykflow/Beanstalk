import openai
import json
import csv
import serpapi

openai.api_key = "sk-proj-6Epr9a95D5UrTp0sps6fT3BlbkFJ2wdCMYoRtGJdPoeTBKWv"
serpapi_key = "15f8a1d2ff687c4ad52b4989221291ee34967e7bd2dec6cf668d27487928c8a0"

def chat_with_ai(query,description_limit,category_limit):
    content=f"""You are a helpful tourist assistant who can answer any question related to tourism and travel and you are designed to output JSON. Follow these guidelines:
    1) Always keep the categories close to the intent of the title, and avoid going into detail in the category words. Keep the category word general.
    2) Return the exact number of answers mentioned in the query.
    3) Output should be in this JSON format: {{
    "data": [
        {{
            "query": "user query",
            "title": "content of the user query. If no result, return N/A.",
            "description": "Detailed description and experience of the place mentioned in the query, limited to exact {description_limit} words",
            "address": "Address of the mentioned in the {query}. In case of no result, return N/A.",
            "categories": "All tags/categories should be related to the user query: "{query}", limited to exact {category_limit} items. If no categories or tags available, return N/A",
            "website": "website of the place mentioned in the query: "{query}". It is important and you have to give the website. If no website is available, return N/A"
        }}

    ]
    }}

    If the query answer contains multiple answers, provide exactly the number of answers requested. For example, if the query asks for 10 answers provide 10 answers, if the query asks for 50 answers provide 50 answers.
    """
    try:
        completion = openai.ChatCompletion.create(
        messages=[
        {"role": "user", "content": content},
    ],
    model="gpt-4o",
    response_format={"type": "json_object"},
    temperature=0.1
)
        data = completion['choices'][0]['message']['content']
        data = json.loads(data)
    
        for item in data['data']:
            try:
                image_title = f"{item['title']} {item['address']}"
                params = {
                    "q": image_title,
                    "engine": "google_images",
                    "ijn": "0",
                    "api_key": serpapi_key,
                }
                search = serpapi.search(params)
                img = search['images_results'][0]['original'] if 'images_results' in search else None
                item["experience-image"] = img
            except:
                item["experience-image"] = "N/A"
        
        fieldnames = ["query", "title", "description", "address", "categories", "website", "image","experience-image"]
        # Preprocess the results to filter out unwanted keys
        processed_results = [{key: item.get(key, 'N/A') for key in fieldnames} for item in data['data']]
        # clean categories data
        clean_categories(processed_results)
        # Write processed results to CSV
        with open("data.csv", "w", newline="", encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(processed_results)

        return {"data": data}
    except Exception as e:
        print(e)
        raise e

def clean_categories(processed_results):
    for category in processed_results:
            if isinstance(category['categories'], list):
                cleaned_categories = ', '.join(category['categories'])
                category['categories'] = cleaned_categories   