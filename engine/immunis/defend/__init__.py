from .features import (
    CATEGORICAL_FEATURES,
    CATEGORICAL_IDX,
    FEATURE_NAMES,
    REASON_TEXT,
    build_features,
)
from .narrative import NarrativeChannel, apply_narrative_channel
from .model import (Detector, RuleLayer, Split, apply_label_noise,
                    prevalence_adjusted_precision, temporal_split)
from .evaluate import (
    REALISTIC_PREVALENCE,
    evaluate,
    permutation_importance_report,
    zero_day_report,
)
from .explain import Explainer
from .stress import narrative_stress_test, novelty_profile

__all__ = [
    "FEATURE_NAMES",
    "CATEGORICAL_FEATURES",
    "CATEGORICAL_IDX",
    "REASON_TEXT",
    "build_features",
    "NarrativeChannel",
    "apply_narrative_channel",
    "Detector",
    "RuleLayer",
    "Split",
    "temporal_split",
    "apply_label_noise",
    "prevalence_adjusted_precision",
    "evaluate",
    "zero_day_report",
    "permutation_importance_report",
    "REALISTIC_PREVALENCE",
    "Explainer",
    "narrative_stress_test",
    "novelty_profile",
]
