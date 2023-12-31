from django.shortcuts import render
from .models import Text
from django.http import HttpResponse
from django.shortcuts import redirect
from .forms import SolveCaptcha 

# main view of site
def home_view(request):
    # Get the URL of the image from Google Drive
    image_id = get_id(service, ORIGIN_ID)
    if not image_id:
        return render(request, 'finished.html')
    url = get_image_url_from_google_drive(service, image_id=image_id)

    if 'rename' in request.POST:
        # get text from django form
        text = request.POST.get('solution')
        current_id = request.POST.get('current_id')
        # move_file_to_folder(service, current_id, folder_id=LIMBO_ID)
        rename_file(service, current_id, text, append=True)
        valid = check_validity(service, current_id, default=text)
        if valid:
            move_file_to_folder(service, current_id, folder_id=DESTINATION_ID)
        else:
            move_file_to_folder(service, current_id, folder_id=ORIGIN_ID)
        return redirect('home')
    if 'skip' in request.POST: #* skipping re-randomizes the captcha selection
        print("skipped")
        return redirect('home')
        

    form = SolveCaptcha()
    context = {'url': url, 'image_id': image_id, 'form': form}

    # Render the template with the URL of the image and the text box
    return render(request, 'home.html', context)

import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
import random

SCOPES = ["https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

# Change to id of 'origin' folder
ORIGIN_ID = '145z3ZP1L2_cFyRbXalgigy9rTTCUNkNz'
# Change to id of 'renamed' folder or subfolder
DESTINATION_ID = "1kmOT0_p6HdoLWd8-_Fim0DNHzxoa8BC3"
# Change to id of 'limbo' folder or subfolder
LIMBO_ID = "1OLsxl_OBkRCU_k1vqO7rBTCjGsoLzCrj"

# Renames file and moves it to success folder
def rename_file(service, image_id, solution, append: bool):
    image = service.files().get(fileId=image_id, fields='name, id').execute()
    if append:
        image_metadata = {"name": image["name"] + '_' + solution}
    else:
        image_metadata = {"name": solution}
    try:
        service.files().update(fileId=image["id"], body=image_metadata).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
    print("successfully renamed")
    return HttpResponse('it worked')

# Function that moves file to destination folder. Does not require origin parameter
def move_file_to_folder(service, file_id, folder_id):
    try:
        # Retrieve the current folder file is in
        file = service.files().get(fileId=file_id, fields="parents").execute()
        previous_parents = ",".join(file.get("parents"))
        # Move the file to the new folder by swapping out old and new 'parent'
        file = service.files().update(fileId=file_id, addParents=folder_id,
                                      removeParents=previous_parents,
                                      fields='id, parents').execute()
        return file.get("parents")

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def check_validity(service, image_id, default):
    image = service.files().get(fileId=image_id, fields='name, id').execute()
    if len(image["name"]) > 200:
        reset_name = f'reset-{default}.png'
        rename_file(service, image_id, reset_name, append=False)
        return False
    prev_names = image["name"].split('_')
    validated_name = find_first_dupe(prev_names)
    if validated_name:
        rename_file(service, image_id, validated_name, append=False)
        return True
    else:
        return False

def find_first_dupe(lst):
    count = {}
    for item in lst:
        if item in count:
            return item
        else:
            count[item] = 1
    return None

# Gets image url from image id to be able to display it
def get_image_url_from_google_drive(service, image_id):

    # Get the URL of the image from Google Drive
    file = service.files().get(fileId=image_id, fields='webContentLink').execute()
    url = file.get('webContentLink')

    # Return the URL of the image
    return url

# Gets random file and returns its id
def get_id(service, origin_id):
    results = service.files().list(q=f"'{origin_id}' in parents and trashed=false and mimeType != 'application/vnd.google-apps.folder'",
                             fields="nextPageToken, files(id, name)").execute()
    items = results.get("files", [])
    if not items:
        return None
    else:
        random_file = random.choice(items)
        return random_file['id']
