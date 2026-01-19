from celery import shared_task
import csv
from api.models import User, Experience,CustomCategory,ExperienceLatLong
from api.models.task_result import TaskResult
from lf_service.category import LifeFrameCategoryService
from api.chat.ai_chat import chat_with_ai,clean_categories
from api.models.save_image import save_image_url
from django.core.files import File
from django.contrib.gis.geos import Point
from api.services.google_maps import GoogleMapsService

@shared_task(bind=True)
def process_experience(self, payload, user_id):
    current_user = User.objects.get(pk=user_id)
    task_result = TaskResult.objects.create(
        user=current_user,
        task_id=self.request.id,
        text=payload["query"],
        status="IN PROGRESS",
        category_limit=payload["category_limit"],
        description_limit=payload["description_limit"],
    )
    try:
        results = chat_with_ai(payload["query"],payload['description_limit'],payload['category_limit'])
        if results:
            file_path = 'data.csv'
            fieldnames = ["query", "title", "description", "address", "categories", "website", "image"]

            # Preprocess the results to filter out unwanted keys
            processed_results = [{key: item.get(key, 'N/A') for key in fieldnames} for item in results['data']['data']]
            # clean categories data
            clean_categories(processed_results)
            with open(file_path, "w", newline="", encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(processed_results)

            with open(file_path, 'r') as csvfile:
                csv_reader = csv.reader(csvfile)
                next(csv_reader)
                for row in csv_reader:
                    if row[4] in ['N/A', ""]:
                        continue
                    try:
                        address = row[3] 
                        service_app = GoogleMapsService().geocode_from_location(address)
                        result = service_app['results'][0]
                        location = result['geometry']['location']
                        latitude = location['lat']
                        longitude = location['lng']
                    except Exception as e:
                        print(f"Error geocoding address {address}: {e}")
                        latitude = None
                        longitude = None
                    lf_server_category = LifeFrameCategoryService().post_new_cat(row[4])
                    print("lf_sever cat:",lf_server_category)
                    # Separate the category IDs and custom category IDs
                    lf_server_category_list = []
                    custom_cat = []

                    for category in lf_server_category:
                        cat_id = category.get('id')
                        cat_name = category.get('name')
                        
                        if cat_id is None:
                            # Create CustomCategory if id is None
                            custom_category= CustomCategory.objects.filter(name=cat_name).first()
                            if custom_category:
                                custom_cat.append(custom_category.id)
                            else:  
                                custom_category= CustomCategory.objects.create(name=cat_name)
                                custom_cat.append(custom_category.id)
                        else:
                            # Check if both id and name exist in the CustomCategory model as a combination
                            if CustomCategory.objects.filter(id=cat_id, name=cat_name).exists():
                                custom_cat.append(cat_id)
                            else:
                                lf_server_category_list.append(cat_id)
                    # img_temp=save_image_url(row[7])
                    # print("temp:",img_temp)
                    print("lifeframe cats:",lf_server_category_list)
                    print("custom cats:",custom_cat)
                    
                    try:
                        experience = Experience.objects.create(
                            created_by=current_user,
                            name=row[1],  # Assuming name is in the second column
                            description=row[2],
                            location=row[3],
                            categories=lf_server_category_list,
                            website=row[5],
                            latitude = latitude,
                            longitude=longitude
                            # experience_image = row[7]
                        )

                        # experience.highlight_image.save("highlight_image.jpg", File(img_temp))
                        # experience.save()
                        # Add custom categories to experience object
                        custom_categories = CustomCategory.objects.filter(id__in=custom_cat)
                        experience.custom_categories.set(custom_categories)
                    except Exception as e:
                        print(f"Failed to create experience for row: {row}, error: {e}")
                        pass

            task_result.status = "FINISHED"
            task_result.save()
            print("Passed to process experience")
        else:
            print("Failed to process experience")
            task_result.status = "FAIL"
            task_result.save()
    except Exception as e:
        print("Exception:", e)
        task_result.status = "FAIL"
        task_result.save()

@shared_task(bind=True)
def delete_custom_categories(self):
    LifeFrameCategoryService().getting_all_categories()
    print("Task run Successfully")
