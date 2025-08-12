-- Dummy data for silver.internal_text_channel_messages table
-- Channels 1 (Project Planning) and 3 (General Team Chat)

-- Channel 1: Project Planning Channel
-- Conversation 1: AI Workshop Planning (15 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(1001, 1, 1, 'Hey team! We need to start planning the AI workshop for next month. Any ideas on what topics we should cover?', '2024-01-15 09:30:00'),
(1002, 3, 1, 'I think we should focus on practical applications this time. Maybe some hands-on coding sessions?', '2024-01-15 09:32:00'),
(1003, 5, 1, 'Great idea! We could do a session on building a simple chatbot or image recognition model', '2024-01-15 09:35:00'),
(1004, 2, 1, 'What about the logistics? Do we have a venue booked yet?', '2024-01-15 09:37:00'),
(1005, 1, 1, 'Not yet, but I was thinking we could use the main conference room. It fits about 30 people', '2024-01-15 09:40:00'),
(1006, 8, 1, 'I can help with the marketing materials and social media promotion', '2024-01-15 09:42:00'),
(1007, 4, 1, 'What''s our budget looking like for this? We might need to order some equipment', '2024-01-15 09:45:00'),
(1008, 1, 1, 'We have about $2000 allocated. Should be enough for basic supplies and refreshments', '2024-01-15 09:47:00'),
(1009, 11, 1, 'I can create the workshop agenda and learning objectives', '2024-01-15 09:50:00'),
(1010, 3, 1, 'Perfect! Let''s aim for February 15th. That gives us about 4 weeks to prepare', '2024-01-15 09:52:00'),
(1011, 5, 1, 'Should we make it a full-day event or half-day?', '2024-01-15 09:55:00'),
(1012, 1, 1, 'I think half-day would work better. 9 AM to 1 PM with lunch included', '2024-01-15 09:57:00'),
(1013, 8, 1, 'I''ll start working on the promotional graphics and registration form', '2024-01-15 10:00:00'),
(1014, 11, 1, 'I''ll draft the workshop outline and send it around for review by end of week', '2024-01-15 10:02:00'),
(1015, 1, 1, 'Excellent! Let''s touch base again next Monday to check progress. Thanks everyone!', '2024-01-15 10:05:00');

-- Conversation 2: Budget Review Meeting (12 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(1016, 9, 1, 'Hi team, we need to review our Q1 budget. Can everyone submit their department expenses by Friday?', '2024-01-16 14:00:00'),
(1017, 2, 1, 'I''ll have the tech team budget ready by Thursday', '2024-01-16 14:02:00'),
(1018, 8, 1, 'Marketing budget is already submitted. We came in under budget by 15%', '2024-01-16 14:05:00'),
(1019, 11, 1, 'Operations budget will be ready by Friday morning', '2024-01-16 14:07:00'),
(1020, 4, 1, 'Any major expenses we should be aware of for Q2?', '2024-01-16 14:10:00'),
(1021, 9, 1, 'We''re planning to upgrade our server infrastructure. That will be about $5000', '2024-01-16 14:12:00'),
(1022, 3, 1, 'Is that included in the current budget or do we need additional funding?', '2024-01-16 14:15:00'),
(1023, 9, 1, 'We have it allocated in Q2 budget, but I want to make sure we have enough buffer', '2024-01-16 14:17:00'),
(1024, 5, 1, 'I can review the technical requirements and see if we can optimize costs', '2024-01-16 14:20:00'),
(1025, 1, 1, 'Let''s schedule a detailed budget review meeting for next Tuesday at 2 PM', '2024-01-16 14:22:00'),
(1026, 8, 1, 'I''ll send out calendar invites for the budget review', '2024-01-16 14:25:00'),
(1027, 9, 1, 'Perfect. Thanks everyone for the quick responses!', '2024-01-16 14:27:00');

-- Conversation 3: New Project Proposal (18 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(1028, 3, 10, 'I have an idea for a new project. What do you think about building a team productivity dashboard?', '2024-01-17 10:30:00'),
(1029, 1, 10, 'That sounds interesting! What would it include?', '2024-01-17 10:32:00'),
(1030, 3, 10, 'Task tracking, time management, team collaboration metrics, and project progress visualization', '2024-01-17 10:35:00'),
(1031, 5, 10, 'We could integrate it with our existing tools like Notion and Discord', '2024-01-17 10:37:00'),
(1032, 2, 10, 'What''s the timeline for this project?', '2024-01-17 10:40:00'),
(1033, 3, 10, 'I estimate 3-4 months for a full MVP. We could have a basic version in 6 weeks', '2024-01-17 10:42:00'),
(1034, 11, 10, 'This could really help with our project management. I''m in!', '2024-01-17 10:45:00'),
(1035, 4, 10, 'What''s the tech stack you''re thinking of using?', '2024-01-17 10:47:00'),
(1036, 3, 10, 'React frontend, Node.js backend, PostgreSQL database. Maybe some AI features for insights', '2024-01-17 10:50:00'),
(1037, 8, 10, 'I can help with the UI/UX design and user research', '2024-01-17 10:52:00'),
(1038, 5, 10, 'We should definitely include some AI-powered analytics. Could be a great selling point', '2024-01-17 10:55:00'),
(1039, 1, 10, 'Let''s create a project proposal document and present it to the board', '2024-01-17 10:57:00'),
(1040, 3, 10, 'I''ll draft the proposal this week and share it with everyone for feedback', '2024-01-17 11:00:00'),
(1041, 9, 10, 'What''s the estimated budget for this project?', '2024-01-17 11:02:00'),
(1042, 3, 10, 'Initial estimate is $15,000 for development and $5,000 for infrastructure', '2024-01-17 11:05:00'),
(1043, 2, 10, 'I can help with the technical architecture and development planning', '2024-01-17 11:07:00'),
(1044, 11, 10, 'Let''s set up a project kickoff meeting once the proposal is ready', '2024-01-17 11:10:00'),
(1045, 1, 10, 'Great initiative! Looking forward to seeing the proposal', '2024-01-17 11:12:00');

-- Conversation 4: Team Structure Discussion (10 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(1046, 1, 1, 'As we grow, we need to think about our team structure. Any thoughts on how we should organize?', '2024-01-18 15:00:00'),
(1047, 9, 1, 'I think we should have clear departments: Tech, Marketing, Operations, and Finance', '2024-01-18 15:02:00'),
(1048, 3, 1, 'What about project-based teams? We could have cross-functional teams for different initiatives', '2024-01-18 15:05:00'),
(1049, 11, 1, 'I like the project-based approach. It keeps things flexible and encourages collaboration', '2024-01-18 15:07:00'),
(1050, 2, 1, 'We should also think about career progression paths for team members', '2024-01-18 15:10:00'),
(1051, 8, 1, 'Agreed! Clear growth opportunities will help with retention', '2024-01-18 15:12:00'),
(1052, 5, 1, 'What about remote work policies? Should we formalize our hybrid approach?', '2024-01-18 15:15:00'),
(1053, 1, 1, 'Good point. Let''s create a working group to draft our organizational structure', '2024-01-18 15:17:00'),
(1054, 4, 1, 'I can help research best practices from other similar organizations', '2024-01-18 15:20:00'),
(1055, 1, 1, 'Perfect! Let''s meet next week to discuss the findings', '2024-01-18 15:22:00');

-- Channel 3: General Team Chat
-- Conversation 1: Weekend Plans (8 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(2001, 8, 3, 'Anyone up for coffee this weekend? I found this great new cafe downtown', '2024-01-19 16:30:00'),
(2002, 5, 3, 'I''m in! What time were you thinking?', '2024-01-19 16:32:00'),
(2003, 11, 3, 'Saturday morning around 10 AM?', '2024-01-19 16:35:00'),
(2004, 2, 3, 'Works for me! Count me in', '2024-01-19 16:37:00'),
(2005, 3, 3, 'I have plans Saturday but maybe next weekend?', '2024-01-19 16:40:00'),
(2006, 8, 3, 'No worries! We can plan another one soon', '2024-01-19 16:42:00'),
(2007, 1, 3, 'Great idea for team bonding!', '2024-01-19 16:45:00'),
(2008, 5, 3, 'I''ll send out the cafe details in a bit', '2024-01-19 16:47:00');

-- Conversation 2: Team Lunch Organization (10 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(2009, 9, 3, 'Don''t forget about the team lunch next week! Any dietary restrictions I should know about?', '2024-01-20 11:00:00'),
(2010, 4, 3, 'I''m vegetarian, but I can usually find something anywhere', '2024-01-20 11:02:00'),
(2011, 8, 3, 'I''m gluten-free. Thanks for asking!', '2024-01-20 11:05:00'),
(2012, 2, 3, 'Where are we going? I heard that new Italian place is good', '2024-01-20 11:07:00'),
(2013, 11, 3, 'I''m allergic to nuts, but I''ll let the restaurant know', '2024-01-20 11:10:00'),
(2014, 9, 3, 'Perfect! I''ll make sure the restaurant can accommodate everyone', '2024-01-20 11:12:00'),
(2015, 5, 3, 'What time is the lunch?', '2024-01-20 11:15:00'),
(2016, 9, 3, '12:30 PM on Thursday. I''ll send calendar invites', '2024-01-20 11:17:00'),
(2017, 1, 3, 'Looking forward to it!', '2024-01-20 11:20:00'),
(2018, 3, 3, 'Thanks for organizing this!', '2024-01-20 11:22:00');

-- Conversation 3: Office Updates (6 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(2019, 1, 3, 'Quick update: The new coffee machine is finally installed!', '2024-01-21 09:00:00'),
(2020, 8, 3, 'Awesome! Can''t wait to try it', '2024-01-21 09:02:00'),
(2021, 2, 3, 'Is it one of those fancy ones with all the options?', '2024-01-21 09:05:00'),
(2022, 1, 3, 'Yes! It has espresso, cappuccino, latte, and even hot chocolate', '2024-01-21 09:07:00'),
(2023, 5, 3, 'Perfect timing for the cold weather', '2024-01-21 09:10:00'),
(2024, 11, 3, 'Thanks for the update!', '2024-01-21 09:12:00');

-- Conversation 4: Social Event Planning (12 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(2025, 8, 3, 'Hey everyone! I was thinking we should plan a team social event. Any ideas?', '2024-01-22 14:00:00'),
(2026, 5, 3, 'What about an escape room? I heard there''s a new one that opened', '2024-01-22 14:02:00'),
(2027, 2, 3, 'That sounds fun! I''m definitely in', '2024-01-22 14:05:00'),
(2028, 11, 3, 'Escape rooms are great for team building. Count me in too', '2024-01-22 14:07:00'),
(2029, 3, 3, 'What about a game night? We could do board games or video games', '2024-01-22 14:10:00'),
(2030, 4, 3, 'I like both ideas! Maybe we could do both on different days?', '2024-01-22 14:12:00'),
(2031, 9, 3, 'Great suggestions! When were you thinking of doing this?', '2024-01-22 14:15:00'),
(2032, 8, 3, 'Maybe next month? We could do escape room one weekend and game night another', '2024-01-22 14:17:00'),
(2033, 1, 3, 'I can help organize the game night. I have some great board games', '2024-01-22 14:20:00'),
(2034, 5, 3, 'Perfect! Let''s plan the escape room for the first weekend of next month', '2024-01-22 14:22:00'),
(2035, 8, 3, 'I''ll check availability and book it. How many people should I reserve for?', '2024-01-22 14:25:00'),
(2036, 2, 3, 'I think most of the team will be interested. Maybe 12-15 people?', '2024-01-22 14:27:00'); 