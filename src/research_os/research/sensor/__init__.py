"""Sensor/Acquisition Plane: passive/semi-passive external census.

Sensors produce SensorObservation records. They never write domain truth.
Observations are UNTRUSTED_EXTERNAL until admitted through the Research
admission chain.
"""

from research_os.research.sensor.archive import WaybackArchiveSensor
from research_os.research.sensor.cert import CertificateMetaSensor
from research_os.research.sensor.ctlog import CTLogSensor
from research_os.research.sensor.dns import DNSSensor
from research_os.research.sensor.techfp import TechnologyFingerprintSensor
from research_os.research.sensor.types import (
    FixtureLoader,
    ScopeCensusView,
    SensorCollectionResult,
    SensorError,
    SensorObservation,
    SensorPort,
    SensorTimeoutError,
)

__all__ = [
    "CertificateMetaSensor",
    "CTLogSensor",
    "DNSSensor",
    "FixtureLoader",
    "ScopeCensusView",
    "SensorCollectionResult",
    "SensorError",
    "SensorObservation",
    "SensorPort",
    "SensorTimeoutError",
    "TechnologyFingerprintSensor",
    "WaybackArchiveSensor",
]
