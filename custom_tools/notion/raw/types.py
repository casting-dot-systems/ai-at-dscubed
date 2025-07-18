from typing import Optional, List, NewType, Dict, Any, Literal
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

# Custom ID types for type safety
EventProjectID = NewType("EventProjectID", str)
TaskID = NewType("TaskID", str)
TeamID = NewType("TeamID", str)
DocumentID = NewType("DocumentID", str)
PersonID = NewType("PersonID", str)

# Database IDs
EVENTS_PROJECTS_DB_ID = "918affd4-ce0d-4b8e-b760-4d972fd24826"
TASKS_DB_ID = "ed8ba37a-719a-47d7-a796-c2d373c794b9"
TEAMS_DB_ID = "139594e5-2bd9-47af-93ca-bb72a35742d2"
DOCUMENTS_DB_ID = "55909df8-1f56-40c4-9327-bab99b4f97f5"

# Events/Projects Database Types
class EventProjectType(Enum):
    NOTE = "c7af628b-b687-4c38-b8ac-8d3172cc58aa"
    EVENT = "79ab91d2-901a-493d-89c4-b5d5d70ab024"
    PROJECT = "bf8121f3-e6aa-4c9c-a915-e8b21cb200a6"
    ADMIN = "fa093f19-64cd-4f7c-ad2a-ed69650ede6d"
    PROGRAM = "ad80bc15-002e-4bed-98a7-70d0ccbdd405"
    PORTFOLIO = "cf8a3888-75ee-4655-b5ed-a263b5515682"
    USER_STORY = "64eeb537-95b8-460d-a6a9-d240cb8f4f67"
    EPIC = "077a77fa-991a-4970-8a53-1292623bacdb"
    SPRINT = "1780f00b-085f-4e65-9023-3406a8cb806f"
    FEATURE = "74bfc6fd-a381-48da-bab1-30460a010218"

class EventProjectProgress(Enum):
    ON_GOING = "b10d8750-5430-4e9a-982b-0b9ef8f9268d"
    PROPOSAL = "d40f9c53-6818-470e-805f-f6575431a933"
    APPROVED = "8e86bc47-37fe-468d-9aa8-a69c016f387d"
    PLANNING = "55c457f3-6430-4616-b338-546fc7b03832"
    IN_PROGRESS = "6f35999d-6364-4409-8b2c-8844a00acc55"
    FINISHED = "2576eecb-5171-4de5-8c11-76910ec79be2"
    CANCELLED = "ab281fe4-971c-4034-8a49-529ff2751844"
    ARCHIVE = "a9d94b23-8214-4b80-81e4-50cba18d8ca5"
    PAUSED = "22b284af-d310-4c94-bd42-df558fe4bbcd"
    TO_REVIEW = "38e64318-438c-4615-acb6-384c3e02ea9e"
    COMPLETE = "975ef4c7-51b8-4e05-8bb7-0cef7586f81f"

class EventProjectPriority(Enum):
    ONE_STAR = "a209e3cd-80e9-45ce-a0b9-953b0c07d20f"
    TWO_STARS = "5b988308-6970-4481-8b14-53c2aae93d88"
    THREE_STARS = "1a525a9b-22be-4519-bc15-be2fc6ac08da"
    FOUR_STARS = "d6115443-adc4-4e39-bcb7-d62f20b4b7e4"
    FIVE_STARS = "0c92bbee-dbdd-413a-853a-ac8818618c7c"

# Tasks Database Types
class TaskStatus(Enum):
    NOT_STARTED = "e07b4872-6baf-464e-8ad9-abf768286e49"
    IN_PROGRESS = "80d361e4-d127-4e1b-b7bf-06e07e2b7890"
    BLOCKED = "rb_~"
    TO_REVIEW = "Q=S~"
    DONE = "`acO"
    ARCHIVE = "aAlA"

class TaskPriority(Enum):
    LOW = "priority_low"
    MEDIUM = "priority_medium"
    HIGH = "priority_high"

# Documents Database Types
class DocumentStatus(Enum):
    NOT_STARTED = "e07b4872-6baf-464e-8ad9-abf768286e49"
    IN_PROGRESS = "80d361e4-d127-4e1b-b7bf-06e07e2b7890"
    BLOCKED = "rb_~"
    DONE = "`acO"
    APPROVED = "^vtK"
    ARCHIVE = "aAlA"

# Property IDs for Events/Projects Database
class EventProjectProperties:
    PARENT_ITEM = "Aqe%5E"
    TYPE = "NU%5BI"
    OWNER = "WM%40J"
    SUB_ITEM = "WjD%7B"
    ALLOCATED = "%5Bgkp"
    TEAM = "%5BnRa"
    TEXT = "%5DIxx"
    PROGRESS = "%60A%3DT"
    PRIORITY = "d%3FzE"
    DESCRIPTION = "gETx"
    DUE_DATES = "qZiF"
    DOCUMENTS = "r%3FOA"
    TASKS = "t%3FT%3A"
    LOCATION = "wemP"
    NAME = "title"

# Property IDs for Tasks Database
class TaskProperties:
    DUE_DATE = "%3Ac%5Dl"
    STATUS = "%3D%3DBK"
    BLOCKING = "%3DBnC"
    DUE_DATES = "JiOy"
    PARENT_TASK = "LA_%5E"
    BLOCKED_BY = "NUHE"
    LAST_EDITED_TIME = "QUy%5B"
    SUB_TASK = "YGx%5B"
    IN_CHARGE = "%5Ca%3Cy"
    IS_DUE = "exOc"
    TASK_PROGRESS = "oP%7BD"
    LAST_EDITED_BY = "tU_i"
    EVENT_PROJECT = "x_Ur"
    TEAM = "zwK%3F"
    NAME = "title"
    PRIORITY = "notion%3A%2F%2Ftasks%2Fpriority_property"
    DESCRIPTION = "notion%3A%2F%2Ftasks%2Fdescription_property"

# Property IDs for Teams Database
class TeamProperties:
    EVENTS_PROJECTS = "EV%3C%5E"
    COVER = "Jj%7B%3A"
    PERSON = "PhyZ"
    COMMITTEE = "qYoJ"
    DOCUMENT = "yd%7D%3B"
    NAME = "title"

# Property IDs for Documents Database
class DocumentProperties:
    EVENTS_PROJECTS = "%3BLwL"
    PARENT_ITEM = "%3D%7D%5Ew"
    LAST_EDITED_BY = "H%5CdT"
    GOOGLE_DRIVE_FILE = "IVfp"
    PERSON = "%5EV%3AS"
    CONTRIBUTORS = "dJG%60"
    TEAM = "fy%3BC"
    PINNED = "p%3Ab%3A"
    OWNED_BY = "u%7Bm%40"
    SUB_ITEM = "y%3DUn"
    NAME = "title"
    IN_CHARGE = "3b64f163-4372-4ad0-b0b1-3ab006c0eb8d"
    STATUS = "7c82316a-6e97-420b-b471-12b462a1944b"

# Complex data types
@dataclass
class NotionDate:
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    time_zone: Optional[str] = None

@dataclass
class RichText:
    content: str
    link: Optional[str] = None

@dataclass
class Person:
    id: PersonID
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None

@dataclass
class EventProject:
    id: EventProjectID
    name: str
    type: Optional[EventProjectType] = None
    progress: Optional[EventProjectProgress] = None
    priority: Optional[EventProjectPriority] = None
    description: Optional[List[RichText]] = None
    text: Optional[List[RichText]] = None
    location: Optional[List[RichText]] = None
    due_dates: Optional[NotionDate] = None
    owner: Optional[List[Person]] = None
    allocated: Optional[List[Person]] = None
    parent_item: Optional[List[EventProjectID]] = None
    sub_item: Optional[List[EventProjectID]] = None
    team: Optional[List[TeamID]] = None
    documents: Optional[List[DocumentID]] = None
    tasks: Optional[List[TaskID]] = None

@dataclass
class Task:
    id: TaskID
    name: str
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    description: Optional[List[RichText]] = None
    task_progress: Optional[List[RichText]] = None
    due_dates: Optional[NotionDate] = None
    in_charge: Optional[List[Person]] = None
    event_project: Optional[List[EventProjectID]] = None
    team: Optional[List[TeamID]] = None
    parent_task: Optional[List[TaskID]] = None
    sub_task: Optional[List[TaskID]] = None
    blocking: Optional[List[TaskID]] = None
    blocked_by: Optional[List[TaskID]] = None

@dataclass
class Team:
    id: TeamID
    name: str
    person: Optional[List[Person]] = None
    cover: Optional[List[str]] = None
    events_projects: Optional[List[EventProjectID]] = None
    committee: Optional[List[str]] = None
    document: Optional[List[DocumentID]] = None

@dataclass
class Document:
    id: DocumentID
    name: str
    status: Optional[DocumentStatus] = None
    person: Optional[List[Person]] = None
    contributors: Optional[List[Person]] = None
    owned_by: Optional[List[Person]] = None
    in_charge: Optional[List[Person]] = None
    team: Optional[List[TeamID]] = None
    events_projects: Optional[List[EventProjectID]] = None
    parent_item: Optional[List[DocumentID]] = None
    sub_item: Optional[List[DocumentID]] = None
    google_drive_file: Optional[List[str]] = None
    pinned: Optional[bool] = None