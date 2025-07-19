-- Table linking committee members to meetings
CREATE TABLE meeting_members (
    meeting_id INTEGER REFERENCES meeting(meeting_id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES committee(member_id) ON DELETE CASCADE,
    PRIMARY KEY (meeting_id, member_id)
); 