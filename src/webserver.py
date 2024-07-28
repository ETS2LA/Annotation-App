#import src.variables as variables
import numpy as np
import requests
import base64
import json
import cv2

'''
batch.json template:

{
    "id": "batch_id",
    "assignee": "username",
    "stage": "stage",
    "state": "state",
}
'''

WEBSERVER_URL = "https://data.ets2la.com/api"
HEADERS = {"Content-Type": "application/json"}

def CheckConnection():
    '''
    Checks if the webserver is online

    Returns:
        dict: A dictionary containing the status of the request
    '''
    request = requests.get(WEBSERVER_URL, headers=HEADERS)
    if request.status_code == 200:
        return {"status": True}
    # Temprorarily hardcoded until we have a heartbeat function (This means the webserver is online but the root does not exist)
    elif request.text == '{"detail":"Not Found"}': 
        return {"status": True}
    else:
        return {"status": False, "error": request.text, "code": request.status_code}
    
def GetClasses():
    '''
    Gets a list of classes from the webserver

    Returns:
        dict: A dictionary containing data with the classes or None if the request failed
    '''
    data = {"path": "/data/classes.txt"}
    request = requests.get(f"{WEBSERVER_URL}/file", data=json.dumps(data), headers=HEADERS)
    if request.status_code == 200:
        return {"status": True, "classes": request.json()["content"]}
    else:
        return {"status": False, "error": request.text, "code": request.status_code}

def GetUserBatches(username):
    '''
    Gets a list of user batches from the webserver

    Args:
        username (str): The username of the user

    Returns:
        dict: A dictionary containing data with the user's batches and status
    '''
    batches = []
    data = {"path": "/data"}

    # Get a list of batch folders from the server
    folder_request = requests.get(f"{WEBSERVER_URL}/folder/list", data=json.dumps(data), headers=HEADERS)
    if folder_request.status_code == 200:
        folders = folder_request.json()["folders"]
        # Check to see if the user has been assigned any batches
        for folder in folder:
            for file in folder["files"]:
                if file["name"] == f"taken.txt":
                    data = {"path": f"{folder['path']}/batch.json"}
                    file_request = requests.get(f"{WEBSERVER_URL}/file", data=json.dumps(data), headers=HEADERS)
                    if file_request.status_code == 200:
                        file_data = file_request.json()["content"]
                        if file_data["assignee"] == username:
                            batches.append(file_data)
                    else:
                        print(f"Request to webserver failed with status code {file_request.status_code}")
                        return {"status": False, "error": file_request.text, "code": file_request.status_code}
    else:
        print(f"Request to webserver failed with status code {folder_request.status_code}")
        return {"status": False, "error": folder_request.text, "code": folder_request.status_code}

    return {"status": True, "batches": batches}

def AssignBatch(username):
    '''
    Assigns a batch to a user

    Args:
        username (str): The username of the user

    Returns:
        dict: A dictionary containing the status of the request and batch ID if successful
    '''
    data = {"path": "/data"}
    lowest_id = 0

    # Get a list of batch folders from the server
    folder_request = requests.get(f"{WEBSERVER_URL}/folder/list", data=json.dumps(data), headers=HEADERS)
    if folder_request.status_code == 200:
        folders = folder_request.json()
        # Check to see if the user has been assigned any batches
        for folder in folders:
            for file in folder["files"]:
                if file["name"] == f"taken.txt":
                    batch_id = int(folder["name"].replace("Batch", ""))
                    if batch_id < lowest_id:
                        lowest_id = batch_id

        batch_id = lowest_id + 1

        # Assign the batch to the user
        json_file_data = {"path": f"/annotations/Batch{batch_id}/batch.json", "data": {"id": batch_id, "assignee": username, "stage": "annotation", "state": "pending"}}
        text_file_data = {"path": f"/annotations/Batch{batch_id}/taken.txt", "data": ""}
        json_request = requests.put(f"{WEBSERVER_URL}/file/modify", data=json.dumps(json_file_data), headers=HEADERS)
        if json_request.status_code == 200:
            text_request = requests.put(f"{WEBSERVER_URL}/file/add", data=json.dumps(text_file_data), headers=HEADERS)
            if text_request.status_code == 200:
                return {"status": True, "batch_id": batch_id}
            else:
                return {"status": False, "error": text_request.text, "code": text_request.status_code}
        else:
            return {"status": False, "error": json_request.text, "code": json_request.status_code}

def UnassignBatch(username, batch_id):
    '''
    Unassigns a batch from a user

    Args:
        username (str): The username of the user

    Returns:
        dict: A dictionary containing the status of the request
    '''
    file_data = {"path": f"/data/Batch{batch_id}/"}
    json_data = {"path": f"/data/Batch{batch_id}/batch.json", "data": {"id": batch_id, "assignee": "", "stage": "annotation", "state": "pending"}}

    # Unassign the batch from the user
    json_modify_request = requests.delete(f"{WEBSERVER_URL}/file/modify", data=json.dumps(json_data), headers=HEADERS)
    if json_modify_request.status_code == 200:
        text_remove_request = requests.delete(f"{WEBSERVER_URL}/file/remove", data=json.dumps(file_data), headers=HEADERS)
        if text_remove_request.status_code == 200:
            return {"status": True} 
        else:
            return {"status": False, "error": text_remove_request.text, "code": text_remove_request.status_code}
    else:
        return {"status": False, "error": json_modify_request.text, "code": json_modify_request.status_code}

def GetImagesAndAnnotations(batch_id):
    '''
    Gets a list of images from the webserver

    Args:
        batch_id (str): The ID of the batch

    Returns:
        dict: A dictionary containing data with the images and annotations or None if the request failed
    '''
    data = {"path": f"/data/Batch{batch_id}"}
    images = []
    annotations = []

    request = requests.get(f"{WEBSERVER_URL}/file/list", data=json.dumps(data), headers=HEADERS)
    if request.status_code == 200:
        for file in request.json()["files"]:
            if file["name"].endswith(".png"):
                image_request = requests.get(f"{WEBSERVER_URL}/file/get", data=json.dumps({"path": f"/data/Batch{batch_id}/{file['name']}"}), headers=HEADERS)
                if image_request.status_code == 200:
                    encoded_string = image_request.json()["content"]
                    byte_data = base64.b64decode(encoded_string)
                    nparr = np.frombuffer(byte_data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    images.append({"image": image, "name": file["name"]})
                    
                    annotation_request = requests.get(f"{WEBSERVER_URL}/file/get", data=json.dumps({"path": f"/data/Batch{batch_id}/{file['name'].replace('.png', '.txt')}"}), headers=HEADERS)
                    if annotation_request.status_code == 200:
                        annotation = annotation_request.json()["content"]
                        annotations.append({"annotation": annotation, "name": file["name"].replace(".png", ".txt")})
                    else:
                        return {"status": False, "error": annotation_request.text, "code": annotation_request.status_code}
                else:
                    return {"status": False, "error": image_request.text, "code": image_request.status_code}
        return {"status": True, "images": images, "annotations": annotations}
    else:
        return {"status": False, "error": request.text, "code": request.status_code}