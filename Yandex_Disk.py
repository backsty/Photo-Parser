import requests
import json
from configparser import ConfigParser
from tqdm import tqdm
from datetime import datetime

config = ConfigParser()
config.read('config.ini')


def get_token_id():
    my_vk_token = config['VK']['token']
    my_vk_id = config['VK']['id']
    my_yandex = config['YANDEX']['token']
    return my_vk_token, my_vk_id, my_yandex


def max_resolution(dict_in_search):
    """Функция возвращает ссылку на фото максимального размера и размер фото"""
    max_res = 0
    element = 0
    for i in range(len(dict_in_search)):
        file_dpi = dict_in_search[i].get('width') * dict_in_search[i].get('height')
        if file_dpi > max_res:
            max_res = file_dpi
            element = i
    url = dict_in_search[element].get('url')
    type_ = dict_in_search[element].get('type')
    return url, type_


def time_convertation(time_unix):
    """Функция преобразует дату загрузки фото в привычный формат"""
    time_bc = datetime.fromtimestamp(time_unix)
    str_time = time_bc.strftime('%Y-%m-%d time %H-%M-%S')
    return str_time


class VkRequests:

    def __init__(self, my_vk_token, my_vk_id, version='5.131'):
        self.token = my_vk_token
        self.id = my_vk_id
        self.version = version
        self.params = {'access_token': my_vk_id, 'v': version}
        self.json, self.export_dict = self.upload_json()

    def _get_profile_photos_url(self):
        url = "https://api.vk.com/method/photos.get"
        params = {
            'owner_id': self.id,
            'album_id': 'profile',
            'photo_sizes': 1,
            'extended': 1,
            'rev': 1,
            'access_token': self.token,
            'v': self.version
        }
        response = requests.get(url=url, params={**self.params, **params}).json()['response']
        info_items = response['items']
        info_count = response['count']
        return info_count, info_items

    def _get_logs_only(self):
        result = {}
        photos_count, photos_items = self._get_profile_photos_url()
        for photo_info in range(photos_count):
            likes_count = photos_items[photo_info]['likes']['count']
            url_download, photo_res = max_resolution(photos_items[photo_info]['sizes'])
            time_warp = time_convertation(photos_items[photo_info]['date'])
            res_value = result.get(likes_count, [])
            res_value.append({'likes_count': likes_count,
                              'name': time_warp,
                              'url_photos': url_download,
                              'size': photo_res,
                              })
            result[likes_count] = res_value
        return result

    def upload_json(self):
        json_list = []
        json_dict = {}
        kol = 0
        photos_dict = self._get_logs_only()
        for key in photos_dict.keys():
            for value in photos_dict[key]:
                file_name = f'{value["likes_count"]} {value["name"]}.jpg'
                json_list.append({'file_name': file_name, 'size': value['size']})
                json_dict[file_name] = photos_dict[key][kol]['url_photos']
        return json_list, json_dict


class YandexApi:

    def __init__(self, folder_name, my_yandex, number):
        self.token = my_yandex
        self.number = number
        self.name = folder_name
        self.url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        self.headers = {'Authorization': f'OAuth {self.token}'}
        self.folder = self._create_folder(folder_name)

    def _create_folder(self, folder_name):
        """Метод для создания папки на Яндекс диске"""
        url = 'https://cloud-api.yandex.net/v1/disk/resources'
        params = {'path': folder_name}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            requests.put(url, headers=self.headers, params=params)
            print(f'\nПапка {folder_name} успешно создана на вашем Яндекс диске!\n')
        else:
            print(f'\nПапка {folder_name} уже существует! Копирование невозможно!\n')
        return folder_name

    def _get_url_for_uploading(self, folder_name):
        """Метод для получения информации (ссылки) для загрузки на Яндекс диск"""
        url = 'https://cloud-api.yandex.net/v1/disk/resources'
        params = {'path': folder_name}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            info = response.json()['_embedded']['items']
            folder_list = []
            for element in info:
                folder_list.append(element['name'])
            return folder_list

    def uploading_photos(self, dict_files):
        """Метод загрузки фотографий на Яндекс диск"""
        files_in_folder = self._get_url_for_uploading(self.folder)
        kol = 0
        for key, i in zip(dict_files.keys(), tqdm(range(self.number))):
            if kol < self.number:
                if key not in files_in_folder:
                    params = {'path': f'{self.folder}/{key}',
                              'url': dict_files[key],
                              'overwrite': 'false'
                              }
                    requests.post(self.url, headers=self.headers, params=params)
                    kol += 1
                else:
                    print(f'Файл {key} уже существует!')
            else:
                break
        print(f'\nЗапрос завершен, количество новых файлов составило: {kol}'
              f'\nВсего файлов в исходном альбоме VK: {len(dict_files)}')


if __name__ == '__main__':
    my_vk_token, my_vk_id, my_yandex = get_token_id()
    my_vk = VkRequests(my_vk_token, my_vk_id)

    vk_example = VkRequests(my_vk_token, my_vk_id)
    list_upload = vk_example.upload_json()

    with open('photo_vk.json', 'w') as outfile:
        json.dump(list_upload, outfile)

    my_yandex = YandexApi('VK_PHOTOS_COPY', my_yandex, 7)
    my_yandex.uploading_photos(my_vk.export_dict)