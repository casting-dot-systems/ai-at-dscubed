import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any
from sqlalchemy import text

# Add the apps/brain directory to the path so we can import pipeline.py
sys.path.append(str(Path(__file__).parent.parent.parent))

from pipeline import Pipeline
from base_transformer import BaseTransformer
from component_transformer import ComponentTransformer
from message_transformer import MessageTransformer
from reaction_transformer import ReactionTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BronzeToSilverTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.component_transformer = ComponentTransformer()
        self.message_transformer = MessageTransformer()
        self.reaction_transformer = ReactionTransformer()
        # Initialize pipeline for silver schema operations
        self.pipeline = Pipeline(schema='silver')
    
    def ensure_tables_exist(self) -> bool:
        """Ensure all required silver tables exist by creating them if needed"""
        try:
            # Define the DDL files to execute (in dependency order)
            ddl_files = [
                'internal_msg_component.sql',
                'internal_msg_message.sql', 
                'internal_msg_reactions.sql'
            ]
            
            # Get the path to silver DDL files
            ddl_dir = Path(__file__).parent.parent.parent.parent.parent / 'libs' / 'brain' / 'silver' / 'DDL'
            
            print("🔨 Ensuring Silver Tables Exist")
            print("=" * 40)
            
            success_count = 0
            for ddl_file in ddl_files:
                ddl_path = ddl_dir / ddl_file
                
                if ddl_path.exists():
                    try:
                        self.pipeline.execute_ddl(str(ddl_path))
                        success_count += 1
                        print(f"✅ Table ready: {ddl_file}")
                    except Exception as e:
                        print(f"❌ Failed to create table from {ddl_file}: {e}")
                        return False
                else:
                    print(f"❌ DDL file not found: {ddl_path}")
                    return False
            
            print(f"📊 {success_count}/{len(ddl_files)} tables ready")
            return success_count == len(ddl_files)
            
        except Exception as e:
            logger.error(f"Error ensuring tables exist: {e}")
            return False
    
    async def run_full_pipeline(self, clear_existing: bool = False) -> Dict[str, Any]:
        """Run the complete transformation pipeline using the individual pipelines"""
        try:
            print("🔄 Starting Bronze to Silver Transformation Pipeline")
            print("=" * 60)
            
            # Step 0: Ensure tables exist
            if not self.ensure_tables_exist():
                return {
                    'success': False,
                    'error': 'Failed to ensure required tables exist'
                }
            
            # Step 1: Get committee mapping
            print("📋 Loading committee member mappings...")
            committee_mapping = await self.get_committee_mapping()
            
            # Step 2: Run component transformer
            print("📥 Processing components...")
            component_result = await self.component_transformer.run_pipeline(clear_existing)
            
            if not component_result['success']:
                print(f"❌ Component pipeline failed: {component_result.get('error')}")
                return component_result
            
            component_mapping = component_result['component_mapping']
            print(f"✅ Processed {component_result['components_processed']} components")
            
            # Step 3: Run message transformer
            print("📥 Processing messages...")
            message_result = await self.message_transformer.run_pipeline(
                committee_mapping, component_mapping, clear_existing
            )
            
            if not message_result['success']:
                print(f"❌ Message pipeline failed: {message_result.get('error')}")
                return message_result
            
            message_mapping = message_result['message_mapping']
            print(f"✅ Processed {message_result['messages_processed']} messages")
            
            # Step 4: Run reaction transformer
            print("📥 Processing reactions...")
            reaction_result = await self.reaction_transformer.run_pipeline(
                committee_mapping, message_mapping, clear_existing
            )
            
            if not reaction_result['success']:
                print(f"❌ Reaction pipeline failed: {reaction_result.get('error')}")
                return reaction_result
            
            print(f"✅ Processed {reaction_result['reactions_processed']} reactions")
            
            # Step 5: Verify results
            print("✅ Verifying transformation results...")
            results = await self.verify_transformation()
            
            return {
                'success': True,
                'components_processed': component_result['components_processed'],
                'messages_processed': message_result['messages_processed'],
                'reactions_processed': reaction_result['reactions_processed'],
                'verification_stats': results
            }
            
        except Exception as e:
            logger.error(f"Full pipeline failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
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
            
            # Count total reactions
            result = await session.execute(text("SELECT COUNT(*) FROM silver.internal_msg_reactions"))
            total_reactions = result.scalar()
            
            # Count reactions by type
            result = await session.execute(text("""
                SELECT reaction, COUNT(*) 
                FROM silver.internal_msg_reactions 
                GROUP BY reaction
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """))
            reaction_counts = {row.reaction: row.count for row in result.fetchall()}
            
            # Count total components
            result = await session.execute(text("SELECT COUNT(*) FROM silver.internal_msg_component"))
            total_components = result.scalar()
            
            # Count components by type
            result = await session.execute(text("""
                SELECT component_type, COUNT(*) 
                FROM silver.internal_msg_component 
                GROUP BY component_type
                ORDER BY COUNT(*) DESC
            """))
            component_type_counts = {row.component_type: row.count for row in result.fetchall()}
            
            # Count components with parents
            result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(parent_component_id) as with_parents,
                    COUNT(*) - COUNT(parent_component_id) as without_parents
                FROM silver.internal_msg_component
            """))
            parent_stats = result.fetchone()
            
            return {
                'total_messages': total_messages,
                'type_counts': type_counts,
                'component_counts': component_counts,
                'total_reactions': total_reactions,
                'reaction_counts': reaction_counts,
                'total_components': total_components,
                'component_type_counts': component_type_counts,
                'parent_stats': {
                    'total': parent_stats.total,
                    'with_parents': parent_stats.with_parents,
                    'without_parents': parent_stats.without_parents
                }
            }
    
    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()
        await self.component_transformer.close()
        await self.message_transformer.close()
        await self.reaction_transformer.close()

async def main():
    parser = argparse.ArgumentParser(description='Bronze to Silver transformation pipeline')
    parser.add_argument('--clear-existing', action='store_true', help='Clear existing data before loading')
    parser.add_argument('--component-only', action='store_true', help='Run only the component transformer')
    parser.add_argument('--message-only', action='store_true', help='Run only the message transformer')
    parser.add_argument('--reaction-only', action='store_true', help='Run only the reaction transformer')
    args = parser.parse_args()
    
    transformer = BronzeToSilverTransformer()
    
    try:
        # Run individual transformers if specified
        if args.component_only:
            print("🔄 Running Component Transformer Only")
            if not transformer.ensure_tables_exist():
                print("❌ Failed to ensure required tables exist")
                return
            result = await transformer.component_transformer.run_pipeline(args.clear_existing)
            if result['success']:
                print(f"✅ Successfully processed {result['components_processed']} components")
            else:
                print(f"❌ Component pipeline failed: {result.get('error')}")
            return
        
        if args.message_only:
            print("🔄 Running Message Transformer Only")
            if not transformer.ensure_tables_exist():
                print("❌ Failed to ensure required tables exist")
                return
            committee_mapping = await transformer.get_committee_mapping()
            component_mapping = await transformer.component_transformer.get_component_mapping()
            result = await transformer.message_transformer.run_pipeline(
                committee_mapping, component_mapping, args.clear_existing
            )
            if result['success']:
                print(f"✅ Successfully processed {result['messages_processed']} messages")
            else:
                print(f"❌ Message pipeline failed: {result.get('error')}")
            return
        
        if args.reaction_only:
            print("🔄 Running Reaction Transformer Only")
            if not transformer.ensure_tables_exist():
                print("❌ Failed to ensure required tables exist")
                return
            committee_mapping = await transformer.get_committee_mapping()
            message_mapping = await transformer.message_transformer.get_message_mapping()
            result = await transformer.reaction_transformer.run_pipeline(
                committee_mapping, message_mapping, args.clear_existing
            )
            if result['success']:
                print(f"✅ Successfully processed {result['reactions_processed']} reactions")
            else:
                print(f"❌ Reaction pipeline failed: {result.get('error')}")
            return
        
        # Run full pipeline
        result = await transformer.run_full_pipeline(args.clear_existing)
        
        if result['success']:
            print("\n📊 Transformation Results:")
            stats = result['verification_stats']
            print(f"Total messages: {stats['total_messages']}")
            print("By message type:")
            for msg_type, count in stats['type_counts'].items():
                print(f"  {msg_type}: {count}")
            print(f"Total reactions: {stats['total_reactions']}")
            print("Top reactions:")
            for reaction, count in list(stats['reaction_counts'].items())[:5]:
                print(f"  {reaction}: {count}")
            print(f"Total components: {stats['total_components']}")
            print("By component type:")
            for comp_type, count in stats['component_type_counts'].items():
                print(f"  {comp_type}: {count}")
            print("Parent-child relationships:")
            print(f"  Total components: {stats['parent_stats']['total']}")
            print(f"  With parents: {stats['parent_stats']['with_parents']}")
            print(f"  Without parents: {stats['parent_stats']['without_parents']}")
            
            print("\n🎉 Bronze to Silver transformation completed successfully!")
        else:
            print(f"❌ Pipeline failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"❌ Pipeline failed: {e}")
    finally:
        await transformer.close()

if __name__ == "__main__":
    asyncio.run(main()) 