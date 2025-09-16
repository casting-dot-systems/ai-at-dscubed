import logging
from datetime import datetime
from typing import List, Dict, Any, Union
from sqlalchemy import text
from base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


class ComponentTransformer(BaseTransformer):
    
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
    
    async def get_bronze_component_data(self) -> List[Dict[str, Any]]:
        """Get data from bronze.discord_channels table"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    server_id,
                    server_name,
                    channel_id,
                    channel_name,
                    channel_created_at,
                    parent_id,
                    section_name,
                    entity_type,
                    ingestion_timestamp
                FROM bronze.discord_channels
                ORDER BY channel_created_at
            """))
            
            data = []
            for row in result.fetchall():
                data.append({
                    'server_id': row.server_id,
                    'server_name': row.server_name,
                    'channel_id': row.channel_id,
                    'channel_name': row.channel_name,
                    'channel_created_at': row.channel_created_at,
                    'parent_id': row.parent_id,
                    'section_name': row.section_name,
                    'entity_type': row.entity_type,
                    'ingestion_timestamp': row.ingestion_timestamp
                })
            
            logger.info(f"Retrieved {len(data)} components from bronze.discord_channels")
            return data
    
    async def get_component_mapping(self) -> Dict[str, int]:
        """Get mapping from bronze channel_id (string) to silver component_id (int)"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT src_component_id, component_id 
                FROM silver.internal_msg_component
            """))
            mapping = {str(row.src_component_id): row.component_id for row in result.fetchall()}
            logger.info(f"Loaded {len(mapping)} component mappings")
            return mapping
    
    def sort_components_by_hierarchy(self, bronze_component_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort components so parents are loaded before children"""
        component_map = {row['channel_id']: row for row in bronze_component_data}
        
        root_components = []
        child_components = []
        
        for row in bronze_component_data:
            if row['parent_id'] is None or row['parent_id'] not in component_map:
                root_components.append(row)
            else:
                child_components.append(row)
        
        sorted_components = root_components + child_components
        
        logger.info(f"Sorted {len(root_components)} root components and {len(child_components)} child components")
        return sorted_components
    
    def transform_component_data(self, bronze_component_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform bronze component data to silver format"""
        silver_component_data = []
        
        for row in bronze_component_data:
            # Initially set parent_component_id to None - will be updated later
            silver_component_row = {
                'src_component_id': str(row['channel_id']),
                'component_type': row['entity_type'],
                'parent_component_id': None,  # Will be updated in update_component_parent_relationships
                'component_name': row['channel_name'],
                'created_at': self.parse_timestamp(row['channel_created_at']),
                'ingestion_timestamp': self.parse_timestamp(row['ingestion_timestamp'])
            }
            
            silver_component_data.append(silver_component_row)
        
        logger.info(f"Transformed {len(silver_component_data)} components to silver format")
        return silver_component_data
    
    async def load_components_to_silver(self, silver_component_data: List[Dict[str, Any]], clear_existing: bool = False) -> bool:
        """Load transformed component data to silver.internal_msg_component table"""
        if not silver_component_data:
            logger.warning("No component data to load")
            return True
        
        try:
            async with self.async_session() as session:
                if clear_existing:
                    await session.execute(text("DELETE FROM silver.internal_msg_component"))
                    logger.info("Cleared existing data from silver.internal_msg_component")
                
                batch_size = 1000
                for i in range(0, len(silver_component_data), batch_size):
                    batch = silver_component_data[i:i + batch_size]
                    
                    insert_stmt = text("""
                        INSERT INTO silver.internal_msg_component 
                        (src_component_id, component_type, parent_component_id, component_name, created_at, ingestion_timestamp)
                        VALUES (:src_component_id, :component_type, :parent_component_id, :component_name, :created_at, :ingestion_timestamp)
                    """)
                    
                    await session.execute(insert_stmt, batch)
                    logger.info(f"Inserted component batch {i//batch_size + 1}/{(len(silver_component_data) + batch_size - 1)//batch_size}")
                
                await session.commit()
                logger.info(f"Successfully loaded {len(silver_component_data)} components to silver.internal_msg_component")
                return True
                
        except Exception as e:
            logger.error(f"Error loading component data to silver: {e}")
            return False
    
    async def update_component_parent_relationships(self, bronze_component_data: List[Dict[str, Any]]) -> bool:
        """Update parent-child relationships after components are loaded"""
        try:
            async with self.async_session() as session:
                result = await session.execute(text("""
                    SELECT src_component_id, component_id 
                    FROM silver.internal_msg_component
                """))
                component_mapping = {str(row.src_component_id): row.component_id for row in result.fetchall()}
                
                for row in bronze_component_data:
                    if row['parent_id']:
                        current_component_id = component_mapping.get(str(row['channel_id']))
                        parent_component_id = component_mapping.get(str(row['parent_id']))
                        
                        if current_component_id and parent_component_id:
                            await session.execute(text("""
                                UPDATE silver.internal_msg_component 
                                SET parent_component_id = :parent_component_id
                                WHERE component_id = :current_component_id
                            """), {
                                'parent_component_id': parent_component_id,
                                'current_component_id': current_component_id
                            })
                        else:
                            logger.warning(f"Could not map parent relationship for channel_id {row['channel_id']} -> parent_id {row['parent_id']}")
                
                await session.commit()
                logger.info("Successfully updated component parent-child relationships")
                return True
                
        except Exception as e:
            logger.error(f"Error updating component parent relationships: {e}")
            return False
    
    async def run_pipeline(self, clear_existing: bool = False) -> Dict[str, Any]:
        """Run the complete component transformation pipeline"""
        try:
            bronze_component_data = await self.get_bronze_component_data()
            
            if not bronze_component_data:
                logger.info("No component data to process")
                return {
                    'success': True,
                    'components_processed': 0,
                    'component_mapping': {}
                }
            
            sorted_component_data = self.sort_components_by_hierarchy(bronze_component_data)
            silver_component_data = self.transform_component_data(sorted_component_data)
            
            success = await self.load_components_to_silver(silver_component_data, clear_existing)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to load components to silver layer'
                }
            
            await self.update_component_parent_relationships(sorted_component_data)
            component_mapping = await self.get_component_mapping()
            
            return {
                'success': True,
                'components_processed': len(silver_component_data),
                'component_mapping': component_mapping
            }
            
        except Exception as e:
            logger.error(f"Component pipeline failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }