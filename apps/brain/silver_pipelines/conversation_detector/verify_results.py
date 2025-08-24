import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../../../../.env')
DATABASE_URL = os.getenv('DATABASE_URL')

# Ensure the DATABASE_URL uses an async driver
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)

async def verify_results():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Check conversations created
        result = await conn.execute(text('SELECT convo_id, convo_summary FROM silver.internal_text_channel_convos ORDER BY convo_id'))
        conversations = result.fetchall()
        
        print("🎯 CONVERSATION DETECTION RESULTS")
        print("=" * 50)
        print(f"Total conversations detected: {len(conversations)}")
        print()
        
        for conv in conversations:
            print(f"📝 Conversation {conv[0]}:")
            print(f"   Summary: {conv[1][:100]}{'...' if len(conv[1]) > 100 else ''}")
            
            # Get participants for this conversation
            result = await conn.execute(text('''
                SELECT c.name 
                FROM silver.internal_text_chnl_convo_members cm
                JOIN silver.committee c ON cm.member_id = c.member_id
                WHERE cm.convo_id = :convo_id
                ORDER BY c.name
            '''), {'convo_id': conv[0]})
            participants = [row[0] for row in result.fetchall()]
            print(f"   Participants: {', '.join(participants)}")
            
            # Get message count for this conversation
            result = await conn.execute(text('''
                SELECT COUNT(*) 
                FROM silver.internal_text_chnl_msg_convo_member 
                WHERE convo_id = :convo_id
            '''), {'convo_id': conv[0]})
            message_count = result.scalar()
            print(f"   Messages: {message_count}")
            print()
        
        # Overall statistics
        result = await conn.execute(text('SELECT COUNT(*) FROM silver.internal_text_chnl_msg_convo_member'))
        total_messages_linked = result.scalar()
        
        result = await conn.execute(text('SELECT COUNT(DISTINCT member_id) FROM silver.internal_text_chnl_convo_members'))
        total_participants = result.scalar()
        
        print("📊 OVERALL STATISTICS")
        print("-" * 30)
        print(f"Total messages linked to conversations: {total_messages_linked}")
        print(f"Total unique participants: {total_participants}")
        print(f"Total conversations: {len(conversations)}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_results()) 