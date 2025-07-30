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
current_dir = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(os.path.join(current_dir, 'libs', 'brain', 'silver', 'DML')):
    parent = os.path.dirname(current_dir)
    if parent == current_dir:
        raise FileNotFoundError("Could not find 'libs/brain/silver/DML' in any parent directory.")
    current_dir = parent

DML_DIR = os.path.join(current_dir, 'libs', 'brain', 'silver', 'DML')
print("DML_DIR being used:", DML_DIR)
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
    channel_id: int = 0

@dataclass
class DetectionStatusEvent(Event):
    status: str = ""
    current_channel: int = 0
    messages_processed: int = 0

@dataclass
class DetectionResultEvent(Event):
    conversations_detected: int = 0
    messages_processed: int = 0
    members_identified: int = 0

# Database Models
class InternalTextChannelConvos(Base):
    __tablename__ = 'internal_text_channel_convos'
    __table_args__ = {'schema': 'silver'}
    convo_id = Column(Integer, primary_key=True, autoincrement=True)
    convo_summary = Column(Text)
    ingestion_timestamp = Column(TIMESTAMP, default=datetime.utcnow)

class InternalTextChnlConvoMembers(Base):
    __tablename__ = 'internal_text_chnl_convo_members'
    __table_args__ = {'schema': 'silver'}
    convo_id = Column(Integer, ForeignKey('silver.internal_text_channel_convos.convo_id', ondelete='CASCADE'), primary_key=True)
    member_id = Column(Integer, ForeignKey('silver.committee.member_id', ondelete='CASCADE'), primary_key=True)
    ingestion_timestamp = Column(TIMESTAMP, default=datetime.utcnow)

class InternalTextChnlMsgConvoMember(Base):
    __tablename__ = 'internal_text_chnl_msg_convo_member'
    __table_args__ = {'schema': 'silver'}
    message_id = Column(BigInteger, primary_key=True)
    member_id = Column(Integer, ForeignKey('silver.committee.member_id', ondelete='CASCADE'))
    convo_id = Column(Integer, ForeignKey('silver.internal_text_channel_convos.convo_id', ondelete='CASCADE'), primary_key=True)
    ingestion_timestamp = Column(TIMESTAMP, default=datetime.utcnow)

class Committee(Base):
    __tablename__ = 'committee'
    __table_args__ = {'schema': 'silver'}
    member_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)

class InternalTextChannelMessages(Base):
    __tablename__ = 'internal_text_channel_messages'
    __table_args__ = {'schema': 'silver'}
    message_id = Column(BigInteger, primary_key=True)
    member_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    message = Column(Text)
    date_created = Column(TIMESTAMP)

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
                channel_id = command.channel_id
            else:
                channel_id = getattr(command, 'channel_id', None)
                if not channel_id:
                    raise ValueError("No channel_id provided in command.")
            
            result = await self.detect_conversations(channel_id)
            return CommandResult(success=True, result=result, session_id=self.session_id)
        except Exception as e:
            logger.error(f"Error in handle_command: {e}")
            return CommandResult(success=False, error=str(e), session_id=self.session_id)

    async def detect_conversations(self, channel_id: int) -> Dict[str, int]:
        """
        Main workflow: detect conversations in a specific channel.
        """
        await self.bus.publish(DetectionStatusEvent(
            status="Starting conversation detection", 
            current_channel=channel_id,
            session_id=self.session_id
        ))

        try:
            # Get new messages for the channel (not already processed)
            new_messages = await self._get_new_messages(channel_id)
            
            if not new_messages:
                await self.bus.publish(DetectionStatusEvent(
                    status="No new messages to process",
                    current_channel=channel_id,
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
                current_channel=channel_id,
                messages_processed=len(new_messages),
                session_id=self.session_id
            ))

            # Process messages with LLM
            conversations = await self._detect_conversations_with_llm(new_messages, channel_id)
            
            if not conversations:
                await self.bus.publish(DetectionStatusEvent(
                    status="No conversations detected by LLM",
                    current_channel=channel_id,
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
            logger.error(f"Error detecting conversations for channel {channel_id}: {e}")
            raise

    async def _get_new_messages(self, channel_id: int) -> List[Dict]:
        """
        Get messages that haven't been processed yet (not in internal_text_chnl_msg_convo_member).
        """
        async with self.async_session() as session:
            # Get messages that are not already linked to conversations
            result = await session.execute(text("""
                SELECT m.message_id, m.member_id, m.channel_id, m.message, m.date_created
                FROM silver.internal_text_channel_messages m
                LEFT JOIN silver.internal_text_chnl_msg_convo_member l ON m.message_id = l.message_id
                WHERE m.channel_id = :channel_id 
                AND l.message_id IS NULL
                ORDER BY m.date_created
            """), {'channel_id': channel_id})
            
            messages = []
            for row in result.fetchall():
                messages.append({
                    'message_id': row.message_id,
                    'member_id': row.member_id,
                    'channel_id': row.channel_id,
                    'message': row.message,
                    'date_created': row.date_created
                })
            
            return messages

    async def _detect_conversations_with_llm(self, messages: List[Dict], channel_id: int) -> List[Dict]:
        """
        Use LLM to detect conversations from messages.
        """
        if not messages:
            return []

        # Format messages for LLM
        formatted_messages = self._format_messages_for_llm(messages)
        
        # Build prompt
        prompt = self._build_conversation_detection_prompt(formatted_messages, channel_id)
        
        try:
            # Get LLM response
            response = await self.model.generate(messages=[{"role": "user", "content": prompt}])
            content = response.raw.choices[0].message.content or "{}"
            
            # Parse LLM response
            conversations = self._parse_llm_response(content, messages)
            
            logger.info(f"LLM detected {len(conversations)} conversations in channel {channel_id}")
            return conversations
            
        except Exception as e:
            logger.error(f"Error in LLM conversation detection: {e}")
            # Fallback: create one conversation with all messages
            return self._create_fallback_conversation(messages)

    def _format_messages_for_llm(self, messages: List[Dict]) -> str:
        """Format messages for LLM input"""
        formatted = []
        for msg in messages:
            # Map dummy member IDs to valid committee member IDs if needed
            actual_member_id = self._map_member_id(msg['member_id'])
            member_name = self.committee_members.get(actual_member_id, {}).get('name', f"Member {msg['member_id']}")
            timestamp = msg['date_created'].strftime('%Y-%m-%d %H:%M:%S')
            formatted.append(f"[{timestamp}] {member_name}: {msg['message']}")
        return "\n".join(formatted)

    def _map_member_id(self, dummy_member_id: int) -> int:
        """Map dummy member IDs to valid committee member IDs"""
        # Simple mapping: dummy ID 1 -> committee ID 48, 2 -> 49, etc.
        # This maps our dummy data (1-11) to actual committee members (48-58)
        mapping = {
            1: 48, 2: 49, 3: 50, 4: 51, 5: 52, 6: 53, 7: 54, 8: 55, 9: 56, 10: 57, 11: 58
        }
        return mapping.get(dummy_member_id, dummy_member_id)

    def _build_conversation_detection_prompt(self, formatted_messages: str, channel_id: int) -> str:
        """Build the LLM prompt for conversation detection"""
        committee_context = "\n".join([f"- {m['name']} (ID: {m['id']})" for m in self.committee_members.values()])
        
        return f"""
You are an expert at analyzing text message conversations and detecting conversation boundaries, topics, and participants.

Available committee members:
{committee_context}

Please analyze the following messages from channel {channel_id} and:

1. **Detect Conversation Boundaries**: Group messages into distinct conversations based on topic changes, time gaps, and conversation flow. Each conversation should have a clear beginning and end.

2. **Identify Participants**: For each conversation, identify which committee members participated (use their member IDs from the list above).

3. **Create Summaries**: Write a concise but informative summary for each conversation that captures the main topics, decisions, and key points discussed.

The messages are ordered chronologically. Use the timestamps as context but rely primarily on topic and conversation flow to determine boundaries.

Messages from Channel {channel_id}:
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
- ONLY use member IDs from the committee list above (48-70 range)
- Write clear, informative summaries
- Group related messages together even if there are time gaps
- If you can't identify specific members, use the member IDs from the actual messages
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
                            # Map the member_id to a valid committee member ID
                            mapped_member_id = self._map_member_id(message['member_id'])
                            
                            # Check if the mapped member_id exists in committee before inserting
                            if mapped_member_id in self.committee_members:
                                session.add(InternalTextChnlMsgConvoMember(
                                    message_id=message['message_id'],
                                    member_id=mapped_member_id,
                                    convo_id=convo.convo_id
                                ))
                                messages_processed += 1
                            else:
                                logger.warning(f"Skipping message {message['message_id']} - mapped member_id {mapped_member_id} not found in committee")
                        
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
    print("This engine will detect conversations in text channel messages using LLM.")
    print()
    
    # Get available channels
    async with engine.async_session() as session:
        result = await session.execute(text("""
            SELECT DISTINCT channel_id, COUNT(*) as message_count
            FROM silver.internal_text_channel_messages
            GROUP BY channel_id
            ORDER BY channel_id
        """))
        channels = result.fetchall()
    
    if not channels:
        print("No channels found with messages.")
        return
    
    print("Available channels:")
    for channel_id, message_count in channels:
        print(f"Channel {channel_id}: {message_count} messages")
    
    print()
    try:
        channel_id = int(input("Enter channel ID to process: ").strip())
    except ValueError:
        print("Invalid channel ID. Exiting.")
        return
    
    if not any(ch[0] == channel_id for ch in channels):
        print(f"Channel {channel_id} not found. Exiting.")
        return
    
    command = DetectConversationsCommand(channel_id=channel_id)
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