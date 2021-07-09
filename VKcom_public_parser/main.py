import os
import json
import requests
import secrets
import youtube_dl
from auth_token import auth_token

POSTS_AMOUNT = 30


def main():
    target_public_name = input("Введите название паблика: ")
    public_posts = fetch_wall_posts_json(target_public_name)
    save_wall_data(public_posts, target_public_name)
    posts_id_list = parse_posts_ids(public_posts, target_public_name)
    print(posts_id_list)
    if len(posts_id_list) == 0:
        print("Nothing new")
    else:
        refresh_posts_database(posts_id_list, target_public_name)
        photo_links = fetch_photos(public_posts, posts_id_list)
        video_links = fetch_videos(public_posts, posts_id_list)

        print(photo_links)
        print(video_links)

        download_photos(photo_links, target_public_name)
        download_videos(video_links, target_public_name)


def fetch_wall_posts_json(public_name):
    target_url = f"https://api.vk.com/method/wall.get?domain={public_name}" \
                 f"&count={POSTS_AMOUNT}&access_token={auth_token}&v=5.131"

    wall_request = requests.get(target_url)

    source_json = wall_request.json()
    posts = source_json["response"]["items"]
    return posts


def save_wall_data(json_to_save, public_name):
    if not os.path.exists(f"{public_name}"):
        os.mkdir(public_name)

    with open(f"{public_name}/{public_name}.json", "w", encoding="utf-8") as file:
        json.dump(json_to_save, file, indent=4, ensure_ascii=False)


def parse_posts_ids(posts_to_parse, public_name):
    already_downloaded = []
    if os.path.exists(f"{public_name}/exist_posts_{public_name}.txt"):
        with open(f"{public_name}/exist_posts_{public_name}.txt") as file:
            already_downloaded = [line.rstrip() for line in file]
            already_downloaded = [int(i) for i in already_downloaded]
            print(already_downloaded)

    new_posts_list = []
    for post in posts_to_parse:
        if post["id"] in already_downloaded:
            continue
        else:
            new_post_id = post["id"]
            new_posts_list.append(new_post_id)
    return new_posts_list


def refresh_posts_database(posts_ids, public_name):
    if not os.path.exists(f"{public_name}/exist_posts_{public_name}.txt"):
        with open(f"{public_name}/exist_posts_{public_name}.txt", "w") as file:
            for i in posts_ids:
                file.write(str(i) + "\n")
    else:
        print("database exist")
        with open(f"{public_name}/exist_posts_{public_name}.txt", "a") as file:
            for i in posts_ids:
                file.write(str(i) + "\n")


def fetch_photos(posts_to_parse, new_ids):
    photo_links_container = []
    for post in posts_to_parse:
        try:
            if "attachments" in post and post["id"] in new_ids:
                post_data = post["attachments"]
                if is_photo(post_data):
                    photo_links = retrieve_photos(post_data)
                    photo_links_container += photo_links
        except Exception:
            print("Something not right")
    return photo_links_container


def fetch_videos(posts_to_parse, new_ids):
    video_links_container = []
    for post in posts_to_parse:
        try:
            if "attachments" in post and post["id"] in new_ids:
                post_data = post["attachments"]
                if is_video(post_data):
                    print("video post id " + str(post["id"]))
                    video_links = retrieve_videos(post_data)
                    video_links_container += video_links
        except Exception:
            print("Something not right")
    return video_links_container


def is_photo(data):
    return data[0]["type"] == "photo"


def is_video(data):
    return data[0]["type"] == "video"


def retrieve_photos(data):
    photos_links_list = []
    if len(data) == 1:
        post_photos = data[0]["photo"]["sizes"]
        size_sorted_photos = sorted(
            post_photos, key=lambda k: k["height"], reverse=True)
        photos_links_list.append(size_sorted_photos[0]["url"])
    else:
        for data_photo_item in data:
            post_photos = data_photo_item["photo"]["sizes"]
            size_sorted_photos = sorted(
                post_photos, key=lambda k: k["height"], reverse=True)
            photos_links_list.append(size_sorted_photos[0]["url"])
    return photos_links_list


def retrieve_videos(data):
    videos_links_list = []

    video_access_key = data[0]["video"]["access_key"]
    video_post_id = data[0]["video"]["id"]
    video_owner_id = data[0]["video"]["owner_id"]
    video_link = f"https://api.vk.com/method/video.get?videos=" \
                 f"{video_owner_id}_{video_post_id}_{video_access_key}" \
                 f"&access_token={auth_token}&v=5.131"
    video_request = requests.get(video_link)
    video_response = video_request.json()
    player_video_link = video_response["response"]["items"][0]["player"]
    videos_links_list.append(player_video_link)
    return videos_links_list


def download_photos(links_list, public_name):
    if not os.path.exists(f"{public_name}/files"):
        os.mkdir(f"{public_name}/files")

    for counter, link in enumerate(links_list):
        link_response = requests.get(link)
        name_hash = secrets.token_urlsafe(16)
        with open(f"{public_name}/files/{name_hash}.jpg", "wb") as img_file:
            img_file.write(link_response.content)


def download_videos(links_list, public_name):
    if not os.path.exists(f"{public_name}/videos"):
        os.mkdir(f"{public_name}/videos")

    for link in links_list:
        name_hash = secrets.token_urlsafe(11)
        try:
            download_options = {"outtmpl": f"{public_name}/videos/{name_hash}.mp4"}
            with youtube_dl.YoutubeDL(download_options) as ydl:
                video_info = ydl.extract_info(link, download=False)
                video_duration = video_info["duration"]
                print(video_duration)
                if video_duration < 300:
                    ydl.download([link])
        except ValueError:
            pass

if __name__ == "__main__":
    main()