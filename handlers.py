import requests
from datetime import date, timedelta
import json
from dateutil import parser

import curl


def get_dates_of_week(params):
    print(f"Calling get_days_of_week {params}")

    input_date = parser.parse(json.loads(params)["current_date"])

    start_of_week = input_date - timedelta(days=input_date.weekday())

    week = []

    # Calculate and print dates for Monday to Friday
    for i in range(5):  # Loop for five days (Monday to Friday)
        current_date = start_of_week + timedelta(days=i)
        week.append(current_date)

    print(f"Week is {week}")

    return week


def get_projects_for_user(user_json):
    user = json.loads(user_json)

    api_url = f"http://localhost:8080/v2/private/project?user={user['email']}"
    response = requests.get(api_url)

    print(response.json())

    return response.json()


def create_project(project_json):
    project = json.loads(project_json)
    project["date"] = date.today().strftime("%Y-%m-%d")
    print(f"Creating a new project {project}")
    api_url = f"http://localhost:8080/v2/private/project"

    response = requests.post(api_url, json=project)

    print(f"Project create response {response}")

    return response.json()


def get_all_employees():
    api_url = f"http://localhost:8080/v2/private/employees"
    response = requests.get(api_url)
    return response.json()


def add_employee(employee_json):
    employee = json.loads(employee_json)
    print(f"Creating a new employee {employee}")
    api_url = f"http://localhost:8080/v2/private/employees"

    response = requests.post(api_url, json=employee)

    return response.json()


def get_all_projects():
    api_url = f"http://localhost:8080/v2/private/project"
    response = requests.get(api_url)

    return response.json()


def assign_project_to_employee(payload_json):
    payload = json.loads(payload_json)
    api_url = f"http://localhost:8080/v2/private/project/{payload['project_code']}"
    response = requests.get(api_url)

    if response.status_code == 400:
        return response.json()

    response_project = response.json()

    if response_project["employees"] is None:
        response_project["employees"] = []

    response_project["employees"].append(payload["email"])

    api_url = "http://localhost:8080/v2/private/project"
    response = requests.post(api_url, json=response_project)

    return response.json()


def add_activities(activity_json):
    activity = json.loads(activity_json)
    api_url = "http://localhost:8080/v2/private/activity-report"

    activities = []

    for act_date in activity["dates"]:
        date_ = parser.parse(act_date)

        activities.append(
            {
                "projectCode": activity["project_code"],
                "activities": [
                    {
                        "title": activity["project_code"],
                        "percentage": activity["work_time"],
                        "type": "Project",
                        "date": date_.strftime("%Y-%m-%d"),
                        "project": {
                            "code": activity["project_code"]
                        }
                    }
                ]
            }
        )

    to_post = {
        "activities": activities,
        "employeeEmail": activity["email"],
        "year": date_.strftime("%Y"),
        "month": date_.strftime("%m")
    }

    print(f"Sending activities {to_post}")
    response = requests.post(api_url, json=to_post)

    return response.json()


def add_absence(activity_json):
    absence = json.loads(activity_json)
    api_url = "http://localhost:8080/v2/private/activity-report"

    date_ = parser.parse(absence["date"])
    to_post = {
        "activities": [
            {
                "activities": [
                    {
                        "title": absence["reason"],
                        "percentage": absence["absence_time"],
                        "type": "Absence",
                        "date": date_.strftime("%Y-%m-%d"),
                        "reason": absence["reason"]
                    }
                ]
            }
        ],
        "employeeEmail": absence["email"],
        "year": date_.strftime("%Y"),
        "month": date_.strftime("%m")
    }

    response = requests.post(api_url, json=to_post)
    curl.parse(response)

    return response.json()


def get_project_activities(params_json):
    params = json.loads(params_json)

    date_ = parser.parse(params["current_date"])
    api_url = f"http://localhost:8080/v2/private/activity-report/{params['current_user']}/{date_.strftime('%Y')}/{date_.strftime('%m')}"

    response = requests.get(api_url)

    return response.json()
