import requests
from django.core.files.temp import NamedTemporaryFile


def save_image_url(image_url):
# image_url = 'https://dynamic-media-cdn.tripadvisor.com/media/photo-o/16/5d/f0/53/photo5jpg.jpg?w=1200&h=-1&s=1'
    img_temp = NamedTemporaryFile(delete=True)

    response = requests.get(image_url)
    img_temp.write(response.content)
    img_temp.flush()
    return img_temp