import os
import asyncio
import re
import json
import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Optional, List, Dict, Tuple
from pathlib import Path
from dotenv import load_dotenv
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, BigInteger, select, text

from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID
from llmgine.llm.models.openai_models import Gpt41Mini
from llmgine.llm.providers.providers import Providers
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.ui.cli.cli import EngineCLI
from llmgine.ui.cli.components import EngineResultComponent

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Find the project root (ai-at-dscubed) dynamically
# current_dir = os.path.abspath(os.path.dirname(__file__))
# while not os.path.exists(os.path.join(current_dir, 'libs', 'brain', 'silver', 'DML')):
#     parent = os.path.dirname(current_dir)
#     if parent == current_dir:
#         raise FileNotFoundError("Could not find 'libs/brain/silver/DML' in any parent directory.")
#     current_dir = parent

# DML_DIR = os.path.join(current_dir, 'libs', 'brain', 'silver', 'DML')
# print("DML_DIR being used:", DML_DIR)
Base = declarative_base()

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../../.env'))
DATABASE_URL = os.getenv('DATABASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Ensure the DATABASE_URL uses an async driver (asyncpg for PostgreSQL)
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
elif DATABASE_URL and DATABASE_URL.startswith('postgresql+psycopg2://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)

@dataclass
class DetectConversationsCommand(Command):
    component_id: int = 0

@dataclass
class DetectionStatusEvent(Event):
    status: str = ""
    current_component: int = 0
    messages_processed: int = 0

@dataclass
class DetectionResultEvent(Event):
    conversations_detected: int = 0
    messages_processed: int = 0
    members_identified: int = 0

# Database Models
class InternalMsgConvos(Base):
    __tablename__ = 'internal_msg_convos'
    __table_args__ = {'schema': 'silver'}
    convo_id = Column(Integer, primary_key=True, autoincrement=True)
    convo_summary = Column(Text)
    ingestion_timestamp = Column(TIMESTAMP, default=datetime.utcnow)

class InternalMsgConvoMembers(Base):
    __tablename__ = 'internal_msg_convo_members'
    __table_args__ = {'schema': 'silver'}
    convo_id = Column(Integer, ForeignKey('silver.internal_msg_convos.convo_id', ondelete='CASCADE'), primary_key=True)
    member_id = Column(Integer, ForeignKey('silver.committee.member_id', ondelete='CASCADE'), primary_key=True)
    ingestion_timestamp = Column(TIMESTAMP, default=datetime.utcnow)

class InternalMsgMessageConvoMember(Base):
    __tablename__ = 'internal_msg_message_convo_member'
    __table_args__ = {'schema': 'silver'}
    message_id = Column(BigInteger, primary_key=True)
    member_id = Column(Integer, ForeignKey('silver.committee.member_id', ondelete='CASCADE'))
    convo_id = Column(Integer, ForeignKey('silver.internal_msg_convos.convo_id', ondelete='CASCADE'), primary_key=True)
    ingestion_timestamp = Column(TIMESTAMP, default=datetime.utcnow)

class Committee(Base):
    __tablename__ = 'committee'
    __table_args__ = {'schema': 'silver'}
    member_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)

class InternalMsgMessage(Base):
    __tablename__ = 'internal_msg_message'
    __table_args__ = {'schema': 'silver'}
    message_id = Column(BigInteger, primary_key=True)
    member_id = Column(BigInteger)
    component_id = Column(BigInteger)
    msg_txt = Column(Text)
    sent_at = Column(TIMESTAMP)
    ingestion_timestamp = Column(TIMESTAMP, default=datetime.utcnow)

class ConversationDetectorEngine:
    def __init__(self, model: Any, session_id: Optional[SessionID] = None):
        """
        Initialize the conversation detector engine.
        """
        self.model = model
        self.session_id = session_id or SessionID(str(uuid.uuid4()))
        self.bus = MessageBus()
        self.engine_id = str(os.urandom(8).hex())
        self.committee_members = None  # Will be loaded asynchronously
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def async_setup(self):
        """Load committee members from database"""
        self.committee_members = await self._load_committee_members_from_db()

    async def _load_committee_members_from_db(self):
        """Load committee members from database"""
        members = {}
        async with self.async_session() as session:
            result = await session.execute(
                select(Committee.member_id, Committee.name)
            )
            for member_id, name in result.fetchall():
                members[member_id] = {'id': member_id, 'name': name}
        return members

    async def handle_command(self, command: Command) -> CommandResult:
        """
        Entrypoint for llmgine command handling.
        """
        try:
            if isinstance(command, DetectConversationsCommand):
                component_id = command.component_id
            else:
                component_id = getattr(command, 'component_id', None)
                if not component_id:
                    raise ValueError("No component_id provided in command.")
            
            result = await self.detect_conversations(component_id)
            return CommandResult(success=True, result=result, session_id=self.session_id)
        except Exception as e:
            logger.error(f"Error in handle_command: {e}")
            return CommandResult(success=False, error=str(e), session_id=self.session_id)

    async def detect_conversations(self, component_id: int) -> Dict[str, int]:
        """
        Main workflow: detect conversations in a specific component.
        """
        await self.bus.publish(DetectionStatusEvent(
            status="Starting conversation detection", 
            current_component=component_id,
            session_id=self.session_id
        ))

        try:
            # Get new messages for the component (not already processed)
            new_messages = await self._get_new_messages(component_id)
            
            if not new_messages:
                await self.bus.publish(DetectionStatusEvent(
                    status="No new messages to process",
                    current_component=component_id,
                    messages_processed=0,
                    session_id=self.session_id
                ))
                return {
                    'conversations_detected': 0,
                    'messages_processed': 0,
                    'members_identified': 0
                }

            await self.bus.publish(DetectionStatusEvent(
                status=f"Found {len(new_messages)} new messages to process",
                current_component=component_id,
                messages_processed=len(new_messages),
                session_id=self.session_id
            ))

            # Process messages with LLM
            conversations = await self._detect_conversations_with_llm(new_messages, component_id)
            
            if not conversations:
                await self.bus.publish(DetectionStatusEvent(
                    status="No conversations detected by LLM",
                    current_component=component_id,
                    messages_processed=len(new_messages),
                    session_id=self.session_id
                ))
                return {
                    'conversations_detected': 0,
                    'messages_processed': len(new_messages),
                    'members_identified': 0
                }

            # Insert conversations into database
            result = await self._insert_conversations_to_db(conversations, new_messages)
            
            await self.bus.publish(DetectionResultEvent(
                conversations_detected=result['conversations_detected'],
                messages_processed=result['messages_processed'],
                members_identified=result['members_identified'],
                session_id=self.session_id
            ))

            return result

        except Exception as e:
            logger.error(f"Error detecting conversations for component {component_id}: {e}")
            raise

    async def _get_new_messages(self, component_id: int) -> List[Dict]:
        """
        Get messages that haven't been processed yet (not in internal_text_chnl_msg_convo_member).
        """
        async with self.async_session() as session:
            # Get messages that are not already linked to conversations
            result = await session.execute(text("""
                SELECT m.message_id, m.member_id, m.component_id, m.message, m.date_created
                FROM silver.internal_text_component_messages m
                LEFT JOIN silver.internal_text_chnl_msg_convo_member l ON m.message_id = l.message_id
                WHERE m.component_id = :component_id 
                AND l.message_id IS NULL
                ORDER BY m.date_created
            """), {'component_id': component_id})
            
            messages = []
            for row in result.fetchall():
                messages.append({
                    'message_id': row.message_id,
                    'member_id': row.member_id,
                    'component_id': row.component_id,
                    'message': row.message,
                    'date_created': row.date_created
                })
            
            return messages

    async def _detect_conversations_with_llm(self, messages: List[Dict], component_id: int) -> List[Dict]:
        """
        Use LLM to detect conversations from messages.
        """
        if not messages:
            return []

        # Format messages for LLM
        formatted_messages = self._format_messages_for_llm(messages)
        
        # Build prompt
        prompt = self._build_conversation_detection_prompt(formatted_messages, component_id)
        
        try:
            # Get LLM response
            response = await self.model.generate(messages=[{"role": "user", "content": prompt}])
            content = response.raw.choices[0].message.content or "{}"
            
            # Parse LLM response
            conversations = self._parse_llm_response(content, messages)
            
            logger.info(f"LLM detected {len(conversations)} conversations in component {component_id}")
            return conversations
            
        except Exception as e:
            logger.error(f"Error in LLM conversation detection: {e}")
            # Fallback: create one conversation with all messages
            return self._create_fallback_conversation(messages)

    def _format_messages_for_llm(self, messages: List[Dict]) -> str:
        """Format messages for LLM input"""
        formatted = []
        for msg in messages:
            member_name = self.committee_members.get(msg['member_id'], {}).get('name', f"Member {msg['member_id']}")
            timestamp = msg['date_created'].strftime('%Y-%m-%d %H:%M:%S')
            formatted.append(f"[{timestamp}] {member_name}: {msg['message']}")
        return "\n".join(formatted)

    def _build_conversation_detection_prompt(self, formatted_messages: str, component_id: int) -> str:
        """Build the LLM prompt for conversation detection"""
        committee_context = "\n".join([f"- {m['name']} (ID: {m['id']})" for m in self.committee_members.values()])
        
        return f"""
You are an expert at analyzing text message conversations and detecting conversation boundaries, topics, and participants.

Available committee members:
{committee_context}

Please analyze the following messages from component {component_id} and:

1. **Detect Conversation Boundaries**: Group messages into distinct conversations based on topic changes, time gaps, and conversation flow.
- Make sure that endings and beginnings are clearly separated.
- Be wary of misgrouping messages at the end of the conversation that are more colloquial and does not explicitly contain the key convo information.
- Look out for interjections in messages that may indicate the start of a new conversation or end of a previous conversation.
- Be careful not to group the last message of a conversation as the first message of a new conversation.

2. **Identify Participants**: For each conversation, identify which committee members participated (use their member IDs from the list above).

3. **Create Summaries**: Write a concise but informative summary for each conversation that captures the main topics, decisions, and key points discussed.

The messages are ordered chronologically. Use the timestamps as context but rely primarily on topic and conversation flow to determine boundaries.

Messages from component {component_id}:
{formatted_messages}

Return your response in this exact JSON format:
{{
    "conversations": [
        {{
            "conversation_id": "conv_1",
            "start_message_index": 0,
            "end_message_index": 5,
            "participant_member_ids": [48, 50, 52],
            "summary": "Discussion about AI workshop planning, including topics to cover and timeline for preparation."
        }},
        {{
            "conversation_id": "conv_2", 
            "start_message_index": 6,
            "end_message_index": 12,
            "participant_member_ids": [49, 51],
            "summary": "Technical discussion about implementing new features in the project."
        }}
    ]
}}

Important:
- Use 0-based indexing for message indices
- Include all messages in conversations (no gaps)
- ONLY use member IDs from the committee list above
- Write clear, informative summaries
- Group related messages together even if there are time gaps
- Use the member IDs from the actual messages when identifying participants
"""

    def _parse_llm_response(self, content: str, messages: List[Dict]) -> List[Dict]:
        """Parse LLM response into conversation structure"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(content)
            
            conversations = []
            for conv in data.get('conversations', []):
                start_idx = conv.get('start_message_index', 0)
                end_idx = conv.get('end_message_index', 0)
                
                # Get messages for this conversation
                conv_messages = messages[start_idx:end_idx + 1]
                
                conversations.append({
                    'conversation_id': conv.get('conversation_id', f"conv_{len(conversations) + 1}"),
                    'messages': conv_messages,
                    'participant_member_ids': conv.get('participant_member_ids', []),
                    'summary': conv.get('summary', 'No summary provided')
                })
            
            return conversations
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.error(f"LLM response: {content}")
            # Fallback: create one conversation with all messages
            return self._create_fallback_conversation(messages)

    def _create_fallback_conversation(self, messages: List[Dict]) -> List[Dict]:
        """Create a fallback conversation when LLM parsing fails"""
        # Get unique member IDs from messages
        member_ids = list(set(msg['member_id'] for msg in messages))
        
        return [{
            'conversation_id': 'conv_fallback',
            'messages': messages,
            'participant_member_ids': member_ids,
            'summary': f'Fallback conversation with {len(messages)} messages from {len(member_ids)} participants'
        }]

    async def _insert_conversations_to_db(self, conversations: List[Dict], all_messages: List[Dict]) -> Dict[str, int]:
        """
        Insert conversations and related data into the database.
        """
        conversations_inserted = 0
        messages_processed = 0
        members_identified = set()
        
        async with self.async_session() as session:
            async with session.begin():
                for conversation in conversations:
                    try:
                        # Insert conversation
                        convo = InternalTextChannelConvos(
                            convo_summary=conversation['summary']
                        )
                        session.add(convo)
                        await session.flush()  # Get convo_id
                        
                        # Insert conversation members (only if they exist in committee)
                        for member_id in conversation['participant_member_ids']:
                            if member_id in self.committee_members:
                                session.add(InternalTextChnlConvoMembers(
                                    convo_id=convo.convo_id,
                                    member_id=member_id
                                ))
                                members_identified.add(member_id)
                        
                        # Insert message-conversation links (only if member exists in committee)
                        for message in conversation['messages']:
                            # Check if the member_id exists in committee before inserting
                            if message['member_id'] in self.committee_members:
                                session.add(InternalTextChnlMsgConvoMember(
                                    message_id=message['message_id'],
                                    member_id=message['member_id'],
                                    convo_id=convo.convo_id
                                ))
                                messages_processed += 1
                            else:
                                logger.warning(f"Skipping message {message['message_id']} - member_id {message['member_id']} not found in committee")
                        
                        conversations_inserted += 1
                        logger.info(f"Inserted conversation {convo.convo_id} with {len(conversation['messages'])} messages")
                        
                    except Exception as e:
                        logger.error(f"Error inserting conversation: {e}")
                        # Continue with next conversation instead of failing completely
                        continue
                
                await session.commit()
        
        return {
            'conversations_detected': conversations_inserted,
            'messages_processed': messages_processed,
            'members_identified': len(members_identified)
        }

async def main():
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    
    model = Gpt41Mini(Providers.OPENAI)
    engine = ConversationDetectorEngine(model)
    await engine.async_setup()
    
    cli = EngineCLI(engine.session_id)
    cli.register_engine(engine)
    cli.register_engine_command(DetectConversationsCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(DetectionStatusEvent)
    
    print("Conversation Detector Engine")
    print("=" * 40)
    print("This engine will detect conversations in text component messages using LLM.")
    print()
    
    # Get available components
    async with engine.async_session() as session:
        result = await session.execute(text("""
            SELECT DISTINCT component_id, COUNT(*) as message_count
            FROM silver.internal_msg_message
            GROUP BY component_id
            ORDER BY component_id
        """))
        components = result.fetchall()
    
    if not components:
        print("No components found with messages.")
        return
    
    print("Available components:")
    for component_id, message_count in components:
        print(f"component {component_id}: {message_count} messages")
    
    print()
    try:
        component_id = int(input("Enter component ID to process: ").strip())
    except ValueError:
        print("Invalid component ID. Exiting.")
        return
    
    if not any(ch[0] == component_id for ch in components):
        print(f"component {component_id} not found. Exiting.")
        return
    
    command = DetectConversationsCommand(component_id=component_id)
    result = await engine.handle_command(command)
    
    if result.success:
        print("\n===== CONVERSATION DETECTION RESULTS =====\n")
        data = result.result
        print(f"Conversations detected: {data['conversations_detected']}")
        print(f"Messages processed: {data['messages_processed']}")
        print(f"Members identified: {data['members_identified']}")
    else:
        print(f"Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(main()) 