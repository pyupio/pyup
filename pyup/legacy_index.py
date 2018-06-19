from bs4 import BeautifulSoup
import re


def get_all_versions(html_response):
    packages = get_all_packages(html_response)
    return list({extract_version(package) for package in packages})


def get_all_packages(html_response):
    soup = BeautifulSoup(html_response, 'html.parser')
    return [a.string for a in soup.find_all('a')]


def _pack_type(package_name):
    return package_name.split('.')[-1]


def remove_extension(version):
    return re.sub(r'\.((tar\..*$)|(zip$))', '', version)


def extract_version(package_name):
    pack_type = _pack_type(package_name)
    if pack_type == 'whl' or pack_type == 'egg':
        version = package_name.split('-')[1]
    else:
        version = package_name.split('-')[-1]
    return remove_extension(version)
