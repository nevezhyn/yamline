import literals
from .mixin import (get_pipeline,
                    get_pipeline_item,
                    Pipeline,
                    Stage,
                    Step,
                    VarsBorg)

version_info = (0, 0, 1)
__version__ = ".".join([str(v) for v in version_info])
