"""
Enumerations for all coded fields in the extraction schema.
Based on RA Task: Missing Data Handling Practices Study, Version 1.0.
"""

from enum import Enum


class PaperStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    SKIPPED = "skipped"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class ClassificationCategory(str, Enum):
    EMPIRICAL_QUANTITATIVE = "Empirical Quantitative (Regression-based)"
    EMPIRICAL_QUALITATIVE = "Empirical Qualitative"
    EMPIRICAL_MIXED = "Empirical Mixed Methods"
    REVIEW_META = "Review / Meta-analysis"
    THEORETICAL_CONCEPTUAL = "Theoretical / Conceptual"
    NON_MANAGEMENT = "Non-management / Out of Scope"
    OTHER = "Other"


class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RelationshipDirection(int, Enum):
    POSITIVE = 1
    NEGATIVE = 2
    CURVILINEAR = 3
    NO_DIRECTION = 4


class DataSource(int, Enum):
    SURVEY = 1
    ARCHIVAL = 2
    CONTENT_ANALYSIS = 3
    EXPERIMENT = 4
    OTHER = 5


class VariableType(int, Enum):
    CONTINUOUS = 1
    BINARY = 2
    COUNT = 3
    ORDINAL = 4
    CATEGORICAL = 5


class MediationMethod(int, Enum):
    BARON_KENNY = 1
    SOBEL = 2
    BOOTSTRAP = 3
    SEM = 4
    OTHER = 5


class ModerationMethod(int, Enum):
    INTERACTION_TERM = 1
    SUBGROUP = 2
    BOTH = 3
    OTHER = 4


class ControlJustification(int, Enum):
    NO_JUSTIFICATION = 0
    PARTIAL = 1
    FULL = 2


class DataType(int, Enum):
    CROSS_SECTIONAL = 1
    PANEL = 2
    TIME_SERIES = 3
    MIXED = 4


class UnitOfAnalysis(int, Enum):
    INDIVIDUAL = 1
    TEAM = 2
    FIRM = 3
    INDUSTRY = 4
    COUNTRY = 5
    DYAD = 6
    OTHER = 7


class ModelType(int, Enum):
    OLS = 1
    LOGIT_PROBIT = 2
    FIXED_EFFECTS = 3
    RANDOM_EFFECTS = 4
    GLS = 5
    GMM = 6
    HLM = 7
    SEM = 8
    COUNT = 9
    HECKMAN = 10
    OTHER = 11


class EndogeneityMethod(int, Enum):
    IV_2SLS = 1
    HECKMAN = 2
    PSM = 3
    DID = 4
    RDD = 5
    GMM = 6
    LAG_DV = 7
    FIXED_EFFECTS = 8
    MULTIPLE = 9
    OTHER = 10


class MissingHandlingMethod(int, Enum):
    LISTWISE = 1
    PAIRWISE = 2
    MEAN_SUBSTITUTION = 3
    REGRESSION_IMPUTATION = 4
    MULTIPLE_IMPUTATION = 5
    FIML = 6
    EM = 7
    HOT_DECK = 8
    NOT_REPORTED = 9
    OTHER = 10


class MissingPattern(int, Enum):
    MCAR = 1
    MAR = 2
    MNAR = 3


class DataAvailability(int, Enum):
    NOT_AVAILABLE = 0
    OPEN_ACCESS = 1
    UPON_REQUEST = 2
    PROPRIETARY_ACCESSIBLE = 3


class ReplicationFeasibility(int, Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    NOT_FEASIBLE = 4
