# Pipeline should be platform agnostic

import pandas as pd
from brain.silver.pipelines.base_pipeline import SilverPipeline

class ChannelMetaPipeline(SilverPipeline):
    """"Transform bronze.XXX_channels → silver.internal_text_channel_meta
        - this should be platform agnostic.
        for now some attributes hard-coded, or contains logic specific to discord bronze tables
    """
    # this transoform function is specific to discord meta data
    def transform(self, bronze_table: pd.DataFrame) -> pd.DataFrame:    
        df = bronze_table.copy()

        # bronze to silver transformations

        # TODO: make this platform agnostic, how to detect platform?
        df['source_name'] = "Discord"

        # Use actual entity_type from bronze data if available, otherwise default to discord_text_channel
        if 'entity_type' in df.columns:
            df['channel_type'] = df['entity_type']
        else:
            df['channel_type'] = 'discord_text_channel'

        # TODO: is this manually written by us or by LLM?
        df['description'] = "___"
        
        # Use parent_id from bronze data - this will be category_id for channels in categories, NULL for root channels
        df['parent_id'] = df.get('parent_id', None)  # Use parent_id from bronze data
        
        # Use section_name from bronze data - this will be the category name for channels in categories, NULL for root channels
        df['section_name'] = df.get('section_name', None)  # Use section_name from bronze data
        
        # Map channel_created_at to date_created
        df['date_created'] = df['channel_created_at']

        return df[['channel_id', 
                   'source_name', 
                   'channel_type',
                   'channel_name',
                   'description',
                   'parent_id',
                   'section_name',
                   'date_created',
                   ]]

    def _detect_channel_type_from_bronze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Alternative approach: Detect channel types from bronze table data.
        This can be used if you want to rely on the bronze table's entity_type column
        instead of detecting from the API directly.
        """
        # Use entity_type from bronze data if available
        if 'entity_type' in df.columns:
            df['channel_type'] = df['entity_type']
        else:
            # Fallback: try to detect from channel names or other attributes
            df['channel_type'] = df['channel_name'].apply(self._infer_channel_type_from_name)
        
        return df
    
    def _infer_channel_type_from_name(self, channel_name: str) -> str:
        """
        Infer channel type from channel name (fallback method).
        This is less reliable than API detection but can be used as backup.
        """
        name_lower = channel_name.lower()
        
        # Common patterns in channel names
        if any(keyword in name_lower for keyword in ['announcement', 'news', 'update']):
            return 'discord_news_channel'  # Could be news channel
        elif any(keyword in name_lower for keyword in ['voice', 'vc', 'call']):
            return 'discord_voice_channel'  # Could be voice channel
        elif any(keyword in name_lower for keyword in ['category', 'cat']):
            return 'discord_section'  # Could be category
        elif any(keyword in name_lower for keyword in ['forum', 'discussion', 'topic']):
            return 'discord_forum'  # Could be forum
        else:
            return 'discord_text_channel'  # default, most channels are text channels