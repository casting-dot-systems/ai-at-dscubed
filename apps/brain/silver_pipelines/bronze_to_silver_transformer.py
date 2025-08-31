import argparse
import os
import asyncio
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

# Ensure the DATABASE_URL uses an async driver
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
elif DATABASE_URL and DATABASE_URL.startswith('postgresql+psycopg2://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BronzeToSilverTransformer:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        
    async def get_committee_mapping(self) -> Dict[int, int]:
        """Get mapping from Discord user ID to committee member ID"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT discord_id, member_id 
                FROM silver.committee 
                WHERE discord_id IS NOT NULL
            """))
            mapping = {row.discord_id: row.member_id for row in result.fetchall()}
            logger.info(f"Loaded {len(mapping)} committee member mappings")
            return mapping
    
    async def get_bronze_data(self) -> List[Dict[str, Any]]:
        """Get data from bronze.discord_chat table"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    chat_id,
                    channel_id,
                    channel_name,
                    thread_name,
                    thread_id,
                    message_id,
                    discord_username,
                    discord_user_id,
                    content,
                    chat_created_at,
                    chat_edited_at,
                    is_thread,
                    ingestion_timestamp
                FROM bronze.discord_chat
                ORDER BY chat_created_at
            """))
            
            data = []
            for row in result.fetchall():
                data.append({
                    'chat_id': row.chat_id,
                    'channel_id': row.channel_id,
                    'channel_name': row.channel_name,
                    'thread_name': row.thread_name,
                    'thread_id': row.thread_id,
                    'message_id': row.message_id,
                    'discord_username': row.discord_username,
                    'discord_user_id': row.discord_user_id,
                    'content': row.content,
                    'chat_created_at': row.chat_created_at,
                    'chat_edited_at': row.chat_edited_at,
                    'is_thread': row.is_thread,
                    'ingestion_timestamp': row.ingestion_timestamp
                })
            
            logger.info(f"Retrieved {len(data)} messages from bronze.discord_chat")
            return data
    
    def transform_data(self, bronze_data: List[Dict[str, Any]], committee_mapping: Dict[int, int]) -> List[Dict[str, Any]]:
        """Transform bronze data to silver format"""
        silver_data = []
        
        for row in bronze_data:
            # Map Discord user ID to committee member ID
            member_id = committee_mapping.get(row['discord_user_id'])
            
            if member_id is None:
                logger.warning(f"No committee member found for Discord user ID {row['discord_user_id']} (username: {row['discord_username']})")
                continue
            
            # Determine message type based on thread status
            message_type = 'thread_message' if row['is_thread'] else 'channel_message'
            
            silver_row = {
                'source_message_id': str(row['message_id']),
                'member_id': member_id,
                'component_id': row['channel_id'],  
                'message_text': row['content'],
                'message_type': message_type,
                'sent_at': row['chat_created_at'],
                'edited_at': row['chat_edited_at'],
                'ingestion_timestamp': row['ingestion_timestamp']
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
                
                # Insert data in batches
                batch_size = 1000
                for i in range(0, len(silver_data), batch_size):
                    batch = silver_data[i:i + batch_size]
                    
                    # Build INSERT statement
                    insert_stmt = text("""
                        INSERT INTO silver.internal_msg_message 
                        (source_message_id, member_id, component_id, message_text, message_type, sent_at, edited_at, ingestion_timestamp)
                        VALUES (:source_message_id, :member_id, :component_id, :message_text, :message_type, :sent_at, :edited_at, :ingestion_timestamp)
                    """)
                    
                    await session.execute(insert_stmt, batch)
                    logger.info(f"Inserted batch {i//batch_size + 1}/{(len(silver_data) + batch_size - 1)//batch_size}")
                
                await session.commit()
                logger.info(f"Successfully loaded {len(silver_data)} messages to silver.internal_msg_message")
                return True
                
        except Exception as e:
            logger.error(f"Error loading data to silver: {e}")
            return False
    
    async def verify_transformation(self) -> Dict[str, int]:
        """Verify the transformation results"""
        async with self.async_session() as session:
            # Count total messages
            result = await session.execute(text("SELECT COUNT(*) FROM silver.internal_msg_message"))
            total_messages = result.scalar()
            
            # Count by message type
            result = await session.execute(text("""
                SELECT message_type, COUNT(*) 
                FROM silver.internal_msg_message 
                GROUP BY message_type
            """))
            type_counts = {row.message_type: row.count for row in result.fetchall()}
            
            # Count by component (channel)
            result = await session.execute(text("""
                SELECT component_id, COUNT(*) 
                FROM silver.internal_msg_message 
                GROUP BY component_id 
                ORDER BY component_id
            """))
            component_counts = {row.component_id: row.count for row in result.fetchall()}
            
            return {
                'total_messages': total_messages,
                'type_counts': type_counts,
                'component_counts': component_counts
            }
    
    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()

async def main():
    parser = argparse.ArgumentParser(description='Bronze to Silver transformation pipeline')
    parser.add_argument('--clear-existing', action='store_true', help='Clear existing data before loading')
    parser.add_argument('--validate-only', action='store_true', help='Only validate, do not load data')
    args = parser.parse_args()
    
    transformer = BronzeToSilverTransformer()
    
    try:
        print("🔄 Starting Bronze to Silver Transformation Pipeline")
        print("=" * 60)
        
        # Step 1: Get committee mapping
        print("📋 Loading committee member mappings...")
        committee_mapping = await transformer.get_committee_mapping()
        
        # Step 2: Get bronze data
        print("📥 Retrieving data from bronze.discord_chat...")
        bronze_data = await transformer.get_bronze_data()
        
        if not bronze_data:
            print("❌ No data found in bronze.discord_chat")
            return
        
        # Step 3: Transform data
        print("🔄 Transforming data to silver format...")
        silver_data = transformer.transform_data(bronze_data, committee_mapping)
        
        if not silver_data:
            print("❌ No data could be transformed (likely due to missing committee mappings)")
            return
        
        # Step 4: Load to silver (if not validate-only)
        if not args.validate_only:
            print("📤 Loading data to silver.internal_msg_message...")
            success = await transformer.load_to_silver(silver_data, args.clear_existing)
            
            if success:
                # Step 5: Verify results
                print("✅ Verifying transformation results...")
                results = await transformer.verify_transformation()
                
                print("\n📊 Transformation Results:")
                print(f"Total messages: {results['total_messages']}")
                print("By message type:")
                for msg_type, count in results['type_counts'].items():
                    print(f"  {msg_type}: {count}")
                print("By component (channel):")
                for component_id, count in results['component_counts'].items():
                    print(f"  Channel {component_id}: {count}")
                
                print("\n🎉 Bronze to Silver transformation completed successfully!")
            else:
                print("❌ Failed to load data to silver layer")
        else:
            print("🔍 Validation mode - data not loaded")
            print(f"Would transform {len(silver_data)} messages")
            print(f"Committee mappings available: {len(committee_mapping)}")
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"❌ Pipeline failed: {e}")
    finally:
        await transformer.close()

if __name__ == "__main__":
    asyncio.run(main()) 