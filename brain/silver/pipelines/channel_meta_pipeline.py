# Pipeline should be platform agnostic

import pandas as pd
from brain.silver.pipelines.base_pipeline import SilverPipeline

class ChannelMetaPipeline(SilverPipeline):
    """"Transform bronze.XXX_channels → silver.internal_text_channel_meta
        - this should be platform agnostic.
        for now it's hard-coded since we're ingesting on discord_channels table
    """
    # this transoform function is specific to discord meta data
    def transform(self, bronze_table: pd.DataFrame) -> pd.DataFrame:    
        df = bronze_table.copy()

        # bronze to silver transformations

        # TODO: make this platform agnostic, how to detect platform?
        df['source_name'] = "Discord"

        # TODO: extract this info from discord application meta table?
        df['channel_type'] = 'discord_channel'

        # TODO: is this manually written by us or by LLM?
        df['description'] = "___"
        
        # Map bronze columns to silver columns
        # Use parent_id from bronze data - this will be category_id for channels in categories, NULL for root channels
        df['parent_id'] = df.get('parent_id', None)  # Use parent_id from bronze data
        
        # Map channel_created_at to date_created
        df['date_created'] = df['channel_created_at']

        return df[['channel_id', 
                   'source_name', 
                   'channel_type',
                   'channel_name',
                   'description',
                   'parent_id',
                   'date_created',
                   ]]