import os

import boto3
import requests
from chalice import Chalice
from slacker import Slacker

app = Chalice(app_name='rekognition-slack-bot')
rekognition = boto3.client('rekognition')


def get_value(att_name: dict):
    if isinstance(att_name['Confidence'], float) and att_name['Confidence'] > 70:
        return att_name['Value']


def extract_value_from_face_detail_json(face_details: dict):
    face_details = face_details['FaceDetails']
    result = "*Total face:{0}*".format(len(face_details))

    for face_detail in face_details:
        attributes = list(face_detail.keys())
        for attribute in attributes:
            if isinstance(face_detail[attribute], dict) and 'Confidence' in face_detail[attribute]:
                result += "\n    {0} : {1}".format(attribute, get_value(face_detail[attribute]))

            elif attribute == "Emotions":
                result += "\n    {0}: {1}".format(attribute, face_detail[attribute][0]['Type'])

            elif attribute == "AgeRange":

                result += "\n    {0}: Between {1} and {2}".format(attribute, face_detail[attribute]['Low'],
                                                                  face_detail[attribute]['High'])
        result += "\n"

    return result


@app.route('/', methods=['GET'])
def index():
    event = app.current_request.query_params
    print(event)
    return event


@app.route('/', methods=['POST'])
def post():
    slack_token = os.environ['slack_key']
    event = app.current_request.json_body
    sc = Slacker(slack_token)

    if 'event' in event:
        if 'user' in event['event']:
            if 'file' in event['event'] \
                    and 'mimetype' in event['event']['file'] \
                    and 'image/' in event['event']['file']['mimetype']:

                url = event['event']['file']['url_private_download']
                header = {'Authorization': 'Bearer ' + slack_token}

                file_content = requests.get(url, headers=header)

                try:
                    rekog_response = rekognition.detect_faces(
                        Image={
                            'Bytes': file_content.content
                        },
                        Attributes=['ALL']
                    )

                    response = sc.chat.post_message(
                        channel=event['event']['user'],
                        text="{0}".format(extract_value_from_face_detail_json(rekog_response))
                    )
                    print(response)
                except Exception as e:
                    print(e)

    print(event)
    return event
