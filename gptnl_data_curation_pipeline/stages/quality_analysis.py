from collections import OrderedDict

from datatrove.executor.base import PipelineExecutor
from datatrove.pipeline.filters.sampler_filter import SamplerFilter
from datatrove.pipeline.stats import StatsMerger
from datatrove.pipeline.stats.config import TopKConfig
from gptnl_quality_analysis import PerplexityStats
from jsonargparse import Namespace

from gptnl_data_curation_pipeline.stage import Stage


class QualityAnalysisStage(Stage):

    def __init__(self):
        super().__init__()
        self._modules = OrderedDict(
            {
                "PerplexityStats": {
                    "cls": PerplexityStats,
                    "default": {
                        "top_k_groups": TopKConfig(
                            top_k_groups=["summary", "histogram"], top_k=100_000
                        )
                    },
                },
                "StatsMerger": {
                    "cls": StatsMerger,
                    "default": {
                        "top_k_config": TopKConfig(
                            top_k_groups=["summary", "histogram"], top_k=100_000
                        )
                    },
                },
            }
        )

    def _set_up_modules(self, args: Namespace):
        """Constructs the modules of each stage based on the CLI arguments used for this stage."""
        for module_name, module in self._modules.items():
            if module_name in args:
                args[module_name].output_folder = self.output_folder
                if module_name == "PerplexityStats":
                    args[module_name].input_folder = (str(self.output_folder),)

                self.active_modules.append(module["cls"](**vars(args[module_name])))
