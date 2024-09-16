import src.variables as variables
import cv2
import os

def _yolo_format(class_id, x1, y1, x2, y2, img_width, img_height):
    # Calculate the center of the bounding box
    center_x = (x1 + x2) / 2 / img_width
    center_y = (y1 + y2) / 2 / img_height
    
    # Calculate the width and height of the bounding box
    width = (x2 - x1) / img_width
    height = (y2 - y1) / img_height
    
    # Return as a string in yolo format
    return f"{class_id} {center_x} {center_y} {width} {height}\n"
    
images_path = os.path.join(variables.PATH, "assets", "Images")
annotations_path = os.path.join(variables.PATH, "assets", "Annotations")

def LoadLocalImages():
    images = os.listdir(images_path)

    for i, image in enumerate(images):
        if not os.path.exists(os.path.join(annotations_path, image.split(".")[0] + ".txt")):
            images[i][1] = cv2.imread(image)

    return images # [["1.pmg", img], ["2.png", img], ...]

def SaveAnnotation(image_name : str, yolo_annotation : list[list[str, int, int, int, int]], img_size : list[int, int]):
    '''
    Saves an annotation to the local server

    Args:
        image_name (str): The name of the image
        yolo_annotation (list[list[str, int, int, int, int]]): The yolo annotation ([[label, x1, y1, x2, y2], ...])
    '''
    annotations = []
    for annotation in yolo_annotation:
        annotations.append(_yolo_format(*annotation, *img_size))

    with open(os.path.join(annotations_path, image_name.split(".")[0] + ".txt"), "w") as f:
        f.writelines(annotations)
        f.close()