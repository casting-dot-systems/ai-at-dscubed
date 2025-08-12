-- Realistic dummy data for silver.internal_msg_message table
-- Using integer member IDs (50-65) for AI@DSCubed committee members
-- Components 10 (Project Planning) and 30 (General Team Chat)

-- Component 10: Project Planning Component
-- Conversation 1: AI Token/Subscription Budget Meeting (15 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(3001, 50, 10, 'Hey team! We need to discuss our AI tool subscriptions and token budgets for Q1. Anyone available for a budget review meeting?', '2024-01-15 10:30:00'),
(3002, 51, 10, 'I''ve been tracking our usage across different platforms. We''re over budget on OpenAI and Anthropic tokens', '2024-01-15 10:32:00'),
(3003, 52, 10, 'What''s our current spend vs budget? I can help analyze the usage patterns', '2024-01-15 10:35:00'),
(3004, 53, 10, 'We''re at about 120% of budget. The new AI features we''re testing are consuming a lot of tokens', '2024-01-15 10:37:00'),
(3005, 54, 10, 'Should we implement usage limits or optimize our prompts? I think we can reduce token consumption by 30%', '2024-01-15 10:40:00'),
(3006, 55, 10, 'I agree with Chi. We can also look into bulk token purchases for better rates', '2024-01-15 10:42:00'),
(3007, 56, 10, 'What about the new Claude subscription? Is it worth the upgrade?', '2024-01-15 10:45:00'),
(3008, 57, 10, 'I''ve been testing Claude Pro and it''s significantly better for our use cases. Worth the investment', '2024-01-15 10:47:00'),
(3009, 58, 10, 'Let''s set up usage monitoring dashboards. I can help build alerts for when we hit 80% of budget', '2024-01-15 10:50:00'),
(3010, 59, 10, 'Great idea! We should also track which projects are consuming the most tokens', '2024-01-15 10:52:00'),
(3011, 60, 10, 'I can create a monthly report template for token usage by project and team member', '2024-01-15 10:55:00'),
(3012, 61, 10, 'What''s our total budget for Q1? I want to make sure we allocate properly', '2024-01-15 10:57:00'),
(3013, 62, 10, 'We have $5000 allocated for AI tools this quarter. Currently at $4200', '2024-01-15 11:00:00'),
(3014, 63, 10, 'Let''s schedule a follow-up meeting next week to review the optimization strategies', '2024-01-15 11:02:00'),
(3015, 64, 10, 'Perfect! I''ll send out calendar invites and prepare the usage analysis', '2024-01-15 11:05:00');

-- Conversation 2: New AI Project Proposal (18 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(3016, 51, 10, 'I have an idea for a new AI project - what do you think about building an automated meeting summarizer?', '2024-01-16 14:00:00'),
(3017, 50, 10, 'That sounds interesting! How would it work with our current meeting setup?', '2024-01-16 14:02:00'),
(3018, 51, 10, 'It would integrate with Discord voice channels and automatically generate summaries, action items, and key decisions', '2024-01-16 14:05:00'),
(3019, 52, 10, 'We could use Whisper for transcription and GPT-4 for summarization. What''s the timeline?', '2024-01-16 14:07:00'),
(3020, 53, 10, 'I estimate 2-3 months for MVP. We could have basic transcription in 4 weeks', '2024-01-16 14:10:00'),
(3021, 54, 10, 'This would be huge for our productivity! I can help with the UI/UX design', '2024-01-16 14:12:00'),
(3022, 55, 10, 'What about privacy concerns? We need to make sure meeting data is secure', '2024-01-16 14:15:00'),
(3023, 56, 10, 'Good point! We should implement end-to-end encryption and user consent features', '2024-01-16 14:17:00'),
(3024, 57, 10, 'I can help with the security architecture. We should also add opt-out options', '2024-01-16 14:20:00'),
(3025, 58, 10, 'What''s the tech stack you''re thinking? Python backend with React frontend?', '2024-01-16 14:22:00'),
(3026, 51, 10, 'Exactly! FastAPI backend, React frontend, PostgreSQL for storage, and Redis for caching', '2024-01-16 14:25:00'),
(3027, 59, 10, 'I can help with the database design and API development', '2024-01-16 14:27:00'),
(3028, 60, 10, 'What''s the estimated budget for this project?', '2024-01-16 14:30:00'),
(3029, 51, 10, 'Initial estimate is $8000 for development and $2000 for infrastructure and API costs', '2024-01-16 14:32:00'),
(3030, 62, 10, 'I can help with project management and timeline planning', '2024-01-16 14:35:00'),
(3031, 63, 10, 'Let''s create a project proposal document and present it to the team', '2024-01-16 14:37:00'),
(3032, 64, 10, 'I''ll draft the proposal this week and share it with everyone for feedback', '2024-01-16 14:40:00'),
(3033, 51, 10, 'Perfect! Looking forward to seeing the detailed proposal', '2024-01-16 14:42:00');

-- Component 30: General Team Chat
-- Conversation 3: Team Lunch Organisation (12 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(4001, 56, 30, 'Hey everyone! I was thinking we should organize a team lunch next week. Any preferences?', '2024-01-17 11:30:00'),
(4002, 54, 30, 'I''m in! What about that new Korean BBQ place downtown?', '2024-01-17 11:32:00'),
(4003, 55, 30, 'I''m vegetarian, but I can usually find something anywhere. Korean BBQ sounds great!', '2024-01-17 11:35:00'),
(4004, 52, 30, 'I''m allergic to shellfish, but I''ll let the restaurant know. When were you thinking?', '2024-01-17 11:37:00'),
(4005, 53, 30, 'How about next Thursday at 12:30 PM? That works well with most people''s schedules', '2024-01-17 11:40:00'),
(4006, 57, 30, 'Perfect! I can help with the reservation. How many people should I book for?', '2024-01-17 11:42:00'),
(4007, 58, 30, 'I think most of the team will be interested. Maybe 15-18 people?', '2024-01-17 11:45:00'),
(4008, 59, 30, 'I''ll send out a poll to confirm numbers and dietary restrictions', '2024-01-17 11:47:00'),
(4009, 60, 30, 'Great idea! I can help coordinate with the restaurant for dietary accommodations', '2024-01-17 11:50:00'),
(4010, 61, 30, 'Should we make it a monthly thing? Team bonding is important', '2024-01-17 11:52:00'),
(4011, 62, 30, 'Absolutely! Monthly team lunches would be great for morale', '2024-01-17 11:55:00'),
(4012, 64, 30, 'I''ll create a recurring calendar event and send out the details', '2024-01-17 11:57:00');

-- Conversation 4: Onboarding Process for New Members (16 messages)
INSERT INTO silver.internal_msg_message (message_id, member_id, component_id, msg_txt, sent_at) VALUES
(4013, 50, 30, 'We have two new members joining next week. Should we review our onboarding process?', '2024-01-18 15:00:00'),
(4014, 51, 30, 'Good idea! Our current process could use some updates. What do you think we should include?', '2024-01-18 15:02:00'),
(4015, 52, 30, 'We should definitely include a tour of our AI tools and projects. That''s our core focus', '2024-01-18 15:05:00'),
(4016, 53, 30, 'I can create a comprehensive onboarding checklist. Should we make it a 2-week process?', '2024-01-18 15:07:00'),
(4017, 54, 30, 'What about buddy system? Each new member gets paired with an experienced team member', '2024-01-18 15:10:00'),
(4018, 55, 30, 'Great idea! I can help create the buddy assignments and schedule', '2024-01-18 15:12:00'),
(4019, 56, 30, 'We should also include our communication protocols and Discord etiquette', '2024-01-18 15:15:00'),
(4020, 57, 30, 'What about project shadowing? Let them sit in on a few meetings to understand our workflow', '2024-01-18 15:17:00'),
(4021, 58, 30, 'I can create a welcome package with all the necessary links and resources', '2024-01-18 15:20:00'),
(4022, 59, 30, 'Should we include a 30-60-90 day plan for their integration into projects?', '2024-01-18 15:22:00'),
(4023, 60, 30, 'Absolutely! Clear milestones will help them feel more confident', '2024-01-18 15:25:00'),
(4024, 61, 30, 'What about our AI ethics guidelines? That''s important for new members to understand', '2024-01-18 15:27:00'),
(4025, 62, 30, 'Great point! I can create a session specifically on our AI principles and best practices', '2024-01-18 15:30:00'),
(4026, 63, 30, 'Should we schedule a team introduction meeting for their first day?', '2024-01-18 15:32:00'),
(4027, 64, 30, 'Perfect! I''ll coordinate the onboarding schedule and send out invites', '2024-01-18 15:35:00'),
(4028, 50, 30, 'Thanks everyone! This will make the onboarding much smoother for our new team members', '2024-01-18 15:37:00'); 