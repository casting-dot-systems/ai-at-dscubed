import logging
from datetime import datetime
from typing import List, Dict, Any, Union
from sqlalchemy import text
from base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


class ReactionTransformer(BaseTransformer):
    
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
    
    async def get_bronze_reaction_data(self) -> List[Dict[str, Any]]:
        """Get data from bronze.discord_reactions table with channel information"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    r.reaction_id,
                    r.message_id,
                    r.reaction,
                    r.ingestion_timestamp,
                    c.discord_username,
                    c.discord_user_id
                FROM bronze.discord_reactions r
                JOIN bronze.discord_chats c ON r.message_id = c.message_id
                ORDER BY r.ingestion_timestamp
            """))
            
            data = []
            for row in result.fetchall():
                data.append({
                    'reaction_id': row.reaction_id,
                    'message_id': row.message_id,
                    'reaction': row.reaction,
                    'ingestion_timestamp': row.ingestion_timestamp,
                    'discord_username': row.discord_username,
                    'discord_user_id': row.discord_user_id
                })
            
            logger.info(f"Retrieved {len(data)} reactions from bronze.discord_reactions")
            return data
    
    def transform_reaction_data(self, bronze_reaction_data: List[Dict[str, Any]], committee_mapping: Dict[str, int], message_mapping: Dict[int, int]) -> List[Dict[str, Any]]:
        """Transform bronze reaction data to silver format"""
        silver_reaction_data = []
        
        for row in bronze_reaction_data:
            member_id = committee_mapping.get(str(row['discord_user_id']))
            
            # Log committee vs non-committee members for debugging
            if member_id is None:
                logger.debug(f"Processing reaction from non-committee member: {row['discord_username']} (ID: {row['discord_user_id']})")
            else:
                logger.debug(f"Processing reaction from committee member: {row['discord_username']} (ID: {row['discord_user_id']}) -> member_id: {member_id}")
            
            silver_message_id = message_mapping.get(row['message_id'])
            
            if silver_message_id is None:
                logger.warning(f"No silver message found for Discord message_id {row['message_id']}")
                continue
            
            silver_reaction_row = {
                'message_id': silver_message_id,
                'src_message_id': row['message_id'],
                'reaction': row['reaction'],
                'member_id': member_id,
                'ingestion_timestamp': self.parse_timestamp(row['ingestion_timestamp'])
            }
            
            silver_reaction_data.append(silver_reaction_row)
        
        logger.info(f"Transformed {len(silver_reaction_data)} reactions to silver format")
        return silver_reaction_data
    
    async def load_reactions_to_silver(self, silver_reaction_data: List[Dict[str, Any]], clear_existing: bool = False) -> bool:
        """Load transformed reaction data to silver.internal_msg_reactions table"""
        if not silver_reaction_data:
            logger.warning("No reaction data to load")
            return True
        
        try:
            async with self.async_session() as session:
                if clear_existing:
                    await session.execute(text("DELETE FROM silver.internal_msg_reactions"))
                    logger.info("Cleared existing data from silver.internal_msg_reactions")
                
                batch_size = 1000
                for i in range(0, len(silver_reaction_data), batch_size):
                    batch = silver_reaction_data[i:i + batch_size]
                    
                    insert_stmt = text("""
                        INSERT INTO silver.internal_msg_reactions 
                        (message_id, src_message_id, reaction, member_id, ingestion_timestamp)
                        VALUES (:message_id, :src_message_id, :reaction, :member_id, :ingestion_timestamp)
                    """)
                    
                    await session.execute(insert_stmt, batch)
                    logger.info(f"Inserted reaction batch {i//batch_size + 1}/{(len(silver_reaction_data) + batch_size - 1)//batch_size}")
                
                await session.commit()
                logger.info(f"Successfully loaded {len(silver_reaction_data)} reactions to silver.internal_msg_reactions")
                return True
                
        except Exception as e:
            logger.error(f"Error loading reaction data to silver: {e}")
            return False
    
    async def run_pipeline(self, committee_mapping: Dict[int, int], message_mapping: Dict[int, int], clear_existing: bool = False) -> Dict[str, Any]:
        """Run the complete reaction transformation pipeline"""
        try:
            bronze_reaction_data = await self.get_bronze_reaction_data()
            
            if not bronze_reaction_data:
                logger.info("No reaction data to process")
                return {
                    'success': True,
                    'reactions_processed': 0
                }
            
            silver_reaction_data = self.transform_reaction_data(bronze_reaction_data, committee_mapping, message_mapping)
            
            if not silver_reaction_data:
                logger.info("No reactions could be transformed (missing mappings)")
                return {
                    'success': True,
                    'reactions_processed': 0
                }
            
            success = await self.load_reactions_to_silver(silver_reaction_data, clear_existing)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to load reactions to silver layer'
                }
            
            return {
                'success': True,
                'reactions_processed': len(silver_reaction_data)
            }
            
        except Exception as e:
            logger.error(f"Reaction pipeline failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }