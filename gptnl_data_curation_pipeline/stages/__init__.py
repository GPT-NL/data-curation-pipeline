from .data_splitting import DataSplittingStage
from .deduplication import DeduplicationStage
from .heuristic_filtering import HeuristicFilteringStage
from .llm_processing import LLMProcessingStage
from .machine_translation import MachineTranslation
from .pii_masking import PIIMaskingStage
from .string_normalization import StringNormalizationStage
from .toxic_language_detection import ToxicLanguageDetectionStage

stages = {
    "data_splitting": {
        "inst": DataSplittingStage(),
        "default_input_folder": "test-data/0. raw",
        "default_output_folder": "test-data/1. split",
        "default_logs_folder": "logs/data_splitting",
    },
    "string_normalization": {
        "inst": StringNormalizationStage(),
        "default_input_folder": "test-data/1. split",
        "default_output_folder": "test-data/2. normalized",
        "default_logs_folder": "logs/string_normalization",
    },
    "heuristic_filtering": {
        "inst": HeuristicFilteringStage(),
        "default_input_folder": "test-data/2. normalized",
        "default_output_folder": "test-data/3. heuristically filtered",
        "default_logs_folder": "logs/heuristic_filtering",
    },
    "pii_masking": {
        "inst": PIIMaskingStage(),
        "default_input_folder": "test-data/3. heuristically filtered",
        "default_output_folder": "test-data/4. pii masked",
        "default_logs_folder": "logs/pii_masking",
    },
    "deduplication": {
        "inst": DeduplicationStage(),
        "default_input_folder": "test-data/4. pii masked",
        "default_output_folder": "test-data/5. deduplicated/final",
        "default_logs_folder": "logs/deduplication",
    },
    "toxic_language_detection": {
        "inst": ToxicLanguageDetectionStage(),
        "default_input_folder": "test-data/5. deduplicated/final",
        "default_output_folder": "test-data/6. toxic language detection",
        "default_logs_folder": "logs/toxic_language_detection",
    },
    "machine_translation": {
        "inst": MachineTranslation(),
        "default_input_folder": "test-data/1. split",
        "default_output_folder": "test-data/9.translated",
        "default_logs_folder": "logs/machine_translation",
    },
    "llm_processing": {
        "inst": LLMProcessingStage(),
        "default_input_folder": "test-data/1. split",
        "default_output_folder": "test-data/9.translated",
        "default_logs_folder": "logs/machine_translation",
    },
}
