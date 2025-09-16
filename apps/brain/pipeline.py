import logging
import os
from pathlib import Path
from typing import Optional, Any, Type, Dict
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy.engine import Engine
import pandas as pd

class Pipeline:
    """Base pipeline class with common functionality."""
    
    def __init__(self, 
                 schema: str = 'bronze',
                 log_level: int = logging.INFO):
        """
        Initialize the pipeline.
        
        Args:
            schema: Target schema name
            log_level: Logging level
        """
        self.setup_logging(log_level)
        self.schema = schema
        self.engine = self._create_db_engine()
        
    def _create_db_engine(self) -> Engine:
        """Create SQLAlchemy engine from environment variables."""
        load_dotenv()
        db_connection = os.getenv("DATABASE_URL")
        if not db_connection:
            raise ValueError("DATABASE_URL must be set in .env file")
        return sa.create_engine(db_connection)
        
    def setup_logging(self, log_level: int) -> None:
        """Configure logging."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def execute_ddl(self, ddl_path: str) -> None:
        """
        Execute DDL script.
        
        Args:
            ddl_path: Path to DDL script
        """
        try:
            with open(ddl_path, 'r') as f:
                ddl = f.read()
            
            with self.engine.connect() as conn:
                conn.execute(sa.text(ddl))
                conn.commit()
                
            self.logger.info(f"Successfully executed DDL: {ddl_path}")
            
        except Exception as e:
            self.logger.error(f"Error executing DDL {ddl_path}: {str(e)}")
            raise
            
    def write_dataframe(self, 
                       df: pd.DataFrame,
                       table_name: str,
                       if_exists: str = 'append',
                       dtype: Optional[dict] = None) -> None:
        """
        Write DataFrame to database.
        
        Args:
            df: DataFrame to write
            table_name: Target table name
            if_exists: How to behave if table exists ('fail', 'replace', 'append')
            dtype: Optional dictionary of column names to SQL types
        """
        try:
            # If dtype not provided, use default pandas to_sql behavior
            # Discord IDs are now stored as strings to match DDL TEXT columns
            if dtype is None:
                dtype = {}
            
            df.to_sql(
                table_name,
                self.engine,
                schema=self.schema,
                if_exists=if_exists,
                index=False,
                dtype=dtype
            )
            self.logger.info(f"Successfully wrote data to {self.schema}.{table_name}")
            
        except Exception as e:
            self.logger.error(f"Error writing to {table_name}: {str(e)}")
            raise

def get_ddl_path(ddl_filename: str) -> str:
    """
    Get the absolute path to a DDL file.
    
    Args:
        ddl_filename: Name of the DDL file (e.g., 'create_bronze_table.sql')
        
    Returns:
        str: Absolute path to the DDL file
    """
    # DDL files are located in libs/brain/bronze/DDL/
    return str(Path(__file__).parent.parent.parent / 'libs' / 'brain' / 'bronze' / 'DDL' / ddl_filename)

def run_pipeline(extractor_class: Type,
                ddl_filename: str,
                table_name: str,
                input_path: str) -> None:
    """
    Run a complete pipeline with the given extractor, DDL, and table.
    
    Args:
        extractor_class: The extractor class to use
        ddl_filename: Name of the DDL file to execute
        table_name: Name of the target table
        input_path: Path to the input file
    """
    # Initialize pipeline
    pipeline = Pipeline(schema='bronze')
    
    # Initialize extractor
    extractor = extractor_class()
    extractor.logger = pipeline.logger
    
    try:
        # Execute DDL
        ddl_path = get_ddl_path(ddl_filename)
        pipeline.execute_ddl(ddl_path)
        
        # Extract and transform data
        df = extractor.parse(input_path)
        
        # Load data
        pipeline.write_dataframe(
            df=df,
            table_name=table_name,
            if_exists='append'
        )
        
        pipeline.logger.info("Pipeline completed successfully")
        
    except Exception as e:
        pipeline.logger.error(f"Pipeline failed: {str(e)}")
        raise 