import logging
from datetime import datetime
from typing import List, Dict, Any, Union
from sqlalchemy import text
from base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


class MessageTransformer(BaseTransformer):
    
    def parse_timestamp(self, timestamp_input: Union[str, datetime]) -> datetime:
        """Parse timestamp string or datetime to datetime object (timezone-naive)"""
        if timestamp_input is None:
            return None
        
        # If already a datetime object, just ensure it's timezone-naive
        if isinstance(timestamp_input, datetime):
            return timestamp_input.replace(tzinfo=None) if timestamp_input.tzinfo else timestamp_input
        
        # If it's a string, parse it
        try:
            timestamp_str = str(timestamp_input)
            # Handle ISO format with timezone - convert to naive datetime
            if timestamp_str.endswith('+00:00'):
                timestamp_str = timestamp_str[:-6]
            elif 'Z' in timestamp_str:
                timestamp_str = timestamp_str.replace('Z', '')
            
            dt = datetime.fromisoformat(timestamp_str)
            # Return timezone-naive datetime
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_input}': {e}")
            return None
    
    async def get_bronze_data(self) -> List[Dict[str, Any]]:
        """Get data from bronze.discord_chats table"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    message_id,
                    channel_id,
                    channel_name,
                    thread_name,
                    thread_id,
                    discord_username,
                    discord_user_id,
                    content,
                    chat_created_at,
                    chat_edited_at,
                    is_thread,
                    ingestion_timestamp
                FROM bronze.discord_chats
                ORDER BY chat_created_at
            """))
            
            data = []
            for row in result.fetchall():
                data.append({
                    'message_id': row.message_id,
                    'channel_id': row.channel_id,
                    'channel_name': row.channel_name,
                    'thread_name': row.thread_name,
                    'thread_id': row.thread_id,
                    'discord_username': row.discord_username,
                    'discord_user_id': row.discord_user_id,
                    'content': row.content,
                    'chat_created_at': row.chat_created_at,
                    'chat_edited_at': row.chat_edited_at,
                    'is_thread': row.is_thread,
                    'ingestion_timestamp': row.ingestion_timestamp
                })
            
            logger.info(f"Retrieved {len(data)} messages from bronze.discord_chats")
            return data
    
    async def get_message_mapping(self) -> Dict[int, int]:
        """Get mapping from Discord message_id to silver message_id"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    b.message_id as discord_message_id,
                    s.message_id as silver_message_id
                FROM bronze.discord_chats b
                JOIN silver.internal_msg_message s ON s.src_message_id = b.message_id
            """))
            mapping = {row.discord_message_id: row.silver_message_id for row in result.fetchall()}
            logger.info(f"Loaded {len(mapping)} message mappings")
            return mapping
    
    def transform_data(self, bronze_data: List[Dict[str, Any]], committee_mapping: Dict[str, int], component_mapping: Dict[str, int] = None) -> List[Dict[str, Any]]:
        """Transform bronze data to silver format"""
        silver_data = []
        
        for row in bronze_data:
            member_id = committee_mapping.get(str(row['discord_user_id']))
            
            # Log committee vs non-committee members for debugging
            if member_id is None:
                logger.debug(f"Processing non-committee member: {row['discord_username']} (ID: {row['discord_user_id']})")
            else:
                logger.debug(f"Processing committee member: {row['discord_username']} (ID: {row['discord_user_id']}) -> member_id: {member_id}")
            
            component_id = None
            if component_mapping:
                silver_component_id = component_mapping.get(str(row['channel_id']))
                if silver_component_id:
                    component_id = silver_component_id
                else:
                    logger.warning(f"No silver component found for channel_id {row['channel_id']} (message_id: {row['message_id']})")
                    continue
            else:
                logger.warning(f"No component mapping available for channel_id {row['channel_id']} (message_id: {row['message_id']})")
                continue
            
            message_type = 'thread_message' if row['is_thread'] else 'channel_message'
            
            silver_row = {
                'src_message_id': str(row['message_id']),  # Use message_id from bronze table
                'member_id': member_id,
                'component_id': component_id,
                'message_txt': row['content'],
                'message_type': message_type,
                'sent_at': self.parse_timestamp(row['chat_created_at']),
                'edited_at': self.parse_timestamp(row['chat_edited_at']),
                'ingestion_timestamp': self.parse_timestamp(row['ingestion_timestamp'])
            }
            
            silver_data.append(silver_row)
        
        logger.info(f"Transformed {len(silver_data)} messages to silver format")
        return silver_data
    
    async def load_to_silver(self, silver_data: List[Dict[str, Any]], clear_existing: bool = False) -> bool:
        """Load transformed data to silver.internal_msg_message table"""
        if not silver_data:
            logger.warning("No data to load")
            return True
        
        try:
            async with self.async_session() as session:
                if clear_existing:
                    await session.execute(text("DELETE FROM silver.internal_msg_message"))
                    logger.info("Cleared existing data from silver.internal_msg_message")
                
                batch_size = 1000
                for i in range(0, len(silver_data), batch_size):
                    batch = silver_data[i:i + batch_size]
                    
                    insert_stmt = text("""
                        INSERT INTO silver.internal_msg_message 
                        (src_message_id, member_id, component_id, message_txt, message_type, sent_at, edited_at, ingestion_timestamp)
                        VALUES (:src_message_id, :member_id, :component_id, :message_txt, :message_type, :sent_at, :edited_at, :ingestion_timestamp)
                    """)
                    
                    await session.execute(insert_stmt, batch)
                    logger.info(f"Inserted batch {i//batch_size + 1}/{(len(silver_data) + batch_size - 1)//batch_size}")
                
                await session.commit()
                logger.info(f"Successfully loaded {len(silver_data)} messages to silver.internal_msg_message")
                return True
                
        except Exception as e:
            logger.error(f"Error loading data to silver: {e}")
            return False
    
    async def run_pipeline(self, committee_mapping: Dict[int, int], component_mapping: Dict[int, int], clear_existing: bool = False) -> Dict[str, Any]:
        """Run the complete message transformation pipeline"""
        try:
            bronze_data = await self.get_bronze_data()
            
            if not bronze_data:
                logger.info("No message data to process")
                return {
                    'success': True,
                    'messages_processed': 0,
                    'message_mapping': {}
                }
            
            silver_data = self.transform_data(bronze_data, committee_mapping, component_mapping)
            
            success = await self.load_to_silver(silver_data, clear_existing)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to load messages to silver layer'
                }
            
            message_mapping = await self.get_message_mapping()
            
            return {
                'success': True,
                'messages_processed': len(silver_data),
                'message_mapping': message_mapping
            }
            
        except Exception as e:
            logger.error(f"Message pipeline failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }