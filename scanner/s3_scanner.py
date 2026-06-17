import boto3
from botocore.exceptions import ClientError


def scan_s3() -> list:
    """
    Scans all S3 buckets for misconfigurations
    """
    s3 = boto3.client("s3")
    results = []

    try:
        buckets = s3.list_buckets().get("Buckets", [])

        for bucket in buckets:
            bucket_name = bucket["Name"]

            bucket_info = {
                "resource_type": "S3",
                "resource_id": bucket_name,
                "name": bucket_name,
                "issues": [],
                "details": {}
            }

            # ─── Check 1: Public Access Block ─────────────────────
            try:
                pab = s3.get_public_access_block(Bucket=bucket_name)
                config = pab["PublicAccessBlockConfiguration"]
                all_blocked = all([
                    config.get("BlockPublicAcls", False),
                    config.get("IgnorePublicAcls", False),
                    config.get("BlockPublicPolicy", False),
                    config.get("RestrictPublicBuckets", False)
                ])
                bucket_info["details"]["public_access_blocked"] = all_blocked

                if not all_blocked:
                    bucket_info["issues"].append({
                        "severity": "WARNING",
                        "check": "Public Access",
                        "problem": "Public access block is not fully enabled",
                        "impact": "Bucket or objects may be publicly accessible",
                        "fix": "Enable 'Block all public access' in S3 bucket settings"
                    })
            except ClientError:
                bucket_info["issues"].append({
                    "severity": "CRITICAL",
                    "check": "Public Access",
                    "problem": "Could not check public access settings",
                    "impact": "Unknown public exposure risk",
                    "fix": "Manually check bucket public access settings in AWS Console"
                })

            # ─── Check 2: Versioning ──────────────────────────────
            try:
                versioning = s3.get_bucket_versioning(Bucket=bucket_name)
                status = versioning.get("Status", "Disabled")
                bucket_info["details"]["versioning"] = status

                if status != "Enabled":
                    bucket_info["issues"].append({
                        "severity": "INFO",
                        "check": "Versioning",
                        "problem": "Versioning is not enabled",
                        "impact": "Cannot recover accidentally deleted or overwritten files",
                        "fix": "Enable versioning: aws s3api put-bucket-versioning --bucket " + bucket_name + " --versioning-configuration Status=Enabled"
                    })
            except ClientError as e:
                bucket_info["details"]["versioning"] = f"Error: {e}"

            # ─── Check 3: Encryption ──────────────────────────────
            try:
                s3.get_bucket_encryption(Bucket=bucket_name)
                bucket_info["details"]["encryption"] = "Enabled"
            except ClientError:
                bucket_info["details"]["encryption"] = "Not configured"
                bucket_info["issues"].append({
                    "severity": "WARNING",
                    "check": "Encryption",
                    "problem": "Server-side encryption not explicitly configured",
                    "impact": "Data may not be encrypted at rest (though AWS now encrypts by default)",
                    "fix": "Enable SSE-S3 or SSE-KMS encryption on the bucket"
                })

            # ─── Check 4: Bucket Logging ──────────────────────────
            try:
                logging_config = s3.get_bucket_logging(Bucket=bucket_name)
                has_logging = "LoggingEnabled" in logging_config
                bucket_info["details"]["access_logging"] = has_logging

                if not has_logging:
                    bucket_info["issues"].append({
                        "severity": "INFO",
                        "check": "Access Logging",
                        "problem": "Access logging not enabled",
                        "impact": "Cannot audit who accessed bucket objects",
                        "fix": "Enable server access logging in bucket properties"
                    })
            except ClientError:
                pass

            # ─── Overall health ───────────────────────────────────
            if not bucket_info["issues"]:
                bucket_info["health"] = "HEALTHY"
            elif any(i["severity"] == "CRITICAL" for i in bucket_info["issues"]):
                bucket_info["health"] = "CRITICAL"
            elif any(i["severity"] == "WARNING" for i in bucket_info["issues"]):
                bucket_info["health"] = "WARNING"
            else:
                bucket_info["health"] = "INFO"

            results.append(bucket_info)

    except Exception as e:
        results.append({
            "resource_type": "S3",
            "resource_id": "SCAN_ERROR",
            "error": str(e),
            "health": "ERROR"
        })

    return results