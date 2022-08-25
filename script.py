import requests
from progress.bar import IncrementalBar
from datetime import datetime
import json
import time

def save_to_json(list_to_save : list):
    photos = {}
    photos['photos'] = list_to_save
    with open('saved_photos.json', 'w', encoding='utf-8') as saving_file:
        json.dump(photos, saving_file, indent=3)
        print('json-файл с данными о фотографиях создан')

def responsing(object, response_result):
    status_code = response_result.status_code
    if status_code == 200:
        print()
        print(object, 'успешно загружен(ы)!')
        print()
    elif status_code == 201:
        print()
        print(object, 'успешно создан(ы) или изменен(ы)!')
        print()
    elif status_code == 400:
        print()
        print(object, 'Некорректные данные.')
        print()
    elif status_code == 404:
        print()
        print(object, 'Не найдено. Скорее всего указана недействительная ссылка!')
        print()
    elif status_code == 403:
        print()
        print(object, 'Недостаточно прав для выполнения операции!')
        print()
    elif status_code == 409:
        print()
        print('Ресурс "path" уже существует.')
        print()
    else:
        print()
        print(object, 'Произошла неизвестная ошибка!')
        print()

class VK:

    def __init__(self, access_token, user_id, version='5.131'):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}
        self.url = 'https://api.vk.com/method/'

    def users_info(self):
        params = {'user_ids': self.id}
        response = requests.get(self.url + 'users.get', params={**self.params, **params})
        return response.json()

    def get_photos(self):
        info = self.users_info()
        if info['response'][0]['can_access_closed']:
            album = input('''Введите какие фотографии требуется сохранить? 
            (0 — фотографии со стены, 1 — фотографии профиля; по умолчанию - 1): ''')
            photos_count = input('Введите количество фотографий, которые требуется сохранить (по умолчанию - 5): ')

            params = {
            'owner_id': self.id,
            'album_id': ['wall', 'profile'][int(album) if album.isdigit() and 0 <= int(album) <= 1 else 1],
            'extended': 1,
            'photo_sizes': 1,
            'count': int(photos_count) if photos_count.isdigit() else 5
            }

            photos_download = requests.get(self.url + 'photos.get', params={**self.params, **params})

            responsing(f"Фото ВК пользователя - {info['response'][0]['first_name']} {info['response'][0]['last_name']}", photos_download)
            return photos_download.json()

        else:

            print('Ошибка, вероятно у пользователя закрыт аккаунт!')

    def filter_photos_links_by_max_size(self, photos: dict):
        sizes = {}
        likes_and_dates = []
        if photos is not None and photos['response']['count'] > 0:
            for photo in photos['response']['items']:
                likes_or_publication_date = str(photo['likes']['count']) if not str(photo['likes']['count']) in likes_and_dates else datetime.utcfromtimestamp(photo['date']).strftime('%Y-%m-%d %Hh%Mm%Ss')
                resolution = 0

                for size in photo['sizes']:
                    if size['height'] * size['width'] > resolution:
                        max_size = size['url']
                        resolution = size['height'] * size['width']
                        size_for_load = size['type']

                if resolution == 0:
                    max_size = size['url']
                    resolution = size['height'] * size['width']
                    size_for_load = size['type']

                sizes.update({max_size : [likes_or_publication_date, size_for_load]})
                likes_and_dates.append(likes_or_publication_date)

            print('Найдено фотографий:', len(sizes))
            return sizes

        else:
            print('Не найдено ни одной фотографии!')
            return None



class YaDisk:
    def __init__(self, yandex_token : str, folder_name : str='vk_photos'):
        self.token = yandex_token
        self.headers = {'Authorization' : self.token}
        self.url = 'https://cloud-api.yandex.net'
        self.resource = '/v1/disk/resources'
        self.folder_name = folder_name
        self.params_for_path = {'path': self.folder_name}
    
    def create_folder(self):
        folder = requests.put(self.url + self.resource, headers=self.headers, params={**self.params_for_path})
        responsing("Папка в Я.Диске", folder)
    
    def upload_photos(self, photos_urls : dict):
        saving_list_for_json = []
        bar = IncrementalBar('Фотографии', max = len(photos_urls))

        for photo in photos_urls:
            picture_upload = requests.post(self.url + self.resource + '/upload', headers=self.headers, params={'path': self.params_for_path['path'] + '/' + str(photos_urls[photo][0]) + '.jpg', 'url': photo})
            time.sleep(2)

            if picture_upload.status_code == 202:
                saving_list_for_json.append({'filename': str(photos_urls[photo][0]) + '.jpg' , 'size': str(photos_urls[photo][1])})
                bar.next()

        print()
        save_to_json(saving_list_for_json)






if __name__ == '__main__':
    with open('data.json', 'r', encoding='utf-8') as tokens:
        data = json.load(tokens)
        vk_token = data[0]['vk_token']
        yandex_token = data[0]['yandex_token']

    user_id = input('Введите id пользователя ВКонтакте:')
    vk = VK(vk_token, user_id)
    yandex = YaDisk(yandex_token)
    photos_for_uploading = vk.filter_photos_links_by_max_size(vk.get_photos())
    if photos_for_uploading is not None and len(photos_for_uploading) > 0:
        yandex.create_folder()
        yandex.upload_photos(photos_for_uploading)