from brain.bronze.src.utils.pipeline import Pipeline

class SilverPipeline(Pipeline):
    def __init__(self, log_level=None):
        # setting pipeline schema to silver in the Pipline class?
        super().__init__(schema="silver", log_level=log_level)
