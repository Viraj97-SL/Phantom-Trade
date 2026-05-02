"""
utils/s3.py
AWS S3 artifact storage for PHANTOM TRADE.
Stores forensics verdicts and oracle theses as audit-grade JSON artifacts.
Non-critical — all calls wrapped in try/except. S3 failure never blocks the pipeline.
"""
import json
import os
from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from utils.logging import get_logger

log = get_logger(__name__)

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        )
    return _s3_client


def _bucket() -> str:
    return os.environ.get("S3_BUCKET", "phantom-trade-avb")


async def store_forensics_artifact(claim_id: str, verdict_dict: dict) -> Optional[str]:
    """Store a ClaimVerdict as JSON artifact in S3 under forensics/verdicts/."""
    try:
        s3 = _get_s3()
        today = datetime.utcnow().strftime("%Y/%m/%d")
        key = f"forensics/verdicts/{today}/{claim_id}.json"

        s3.put_object(
            Bucket=_bucket(),
            Key=key,
            Body=json.dumps(verdict_dict, default=str, indent=2).encode("utf-8"),
            ContentType="application/json",
            Metadata={
                "claim_id": claim_id,
                "verdict": str(verdict_dict.get("verdict", "")),
                "confidence": str(verdict_dict.get("confidence", "")),
                "pipeline": "phantom-trade-forensics",
            },
        )
        url = f"s3://{_bucket()}/{key}"
        log.info("Forensics artifact stored in S3", claim_id=claim_id, s3_key=key)
        return url
    except NoCredentialsError:
        log.warning("S3 upload skipped - no AWS credentials")
        return None
    except ClientError as exc:
        log.warning("S3 upload failed", claim_id=claim_id, error=str(exc))
        return None
    except Exception as exc:
        log.warning("S3 artifact storage error", error=str(exc))
        return None


async def store_oracle_artifact(material: str, thesis_dict: dict) -> Optional[str]:
    """Store a MaterialThesis as JSON artifact in S3 under oracle/theses/."""
    try:
        s3 = _get_s3()
        ts = datetime.utcnow().strftime("%Y/%m/%d/%H%M%S")
        key = f"oracle/theses/{material}/{ts}.json"

        s3.put_object(
            Bucket=_bucket(),
            Key=key,
            Body=json.dumps(thesis_dict, default=str, indent=2).encode("utf-8"),
            ContentType="application/json",
            Metadata={
                "material": material,
                "risk_level": str(thesis_dict.get("risk_level", "")),
                "pipeline": "phantom-trade-oracle",
            },
        )
        log.info("Oracle artifact stored in S3", material=material, s3_key=key)
        return f"s3://{_bucket()}/{key}"
    except Exception as exc:
        log.warning("S3 oracle artifact storage error", error=str(exc))
        return None
