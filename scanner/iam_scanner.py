import boto3
from datetime import datetime, timezone


def scan_iam() -> list:
    """
    Scans IAM for basic security issues
    """
    iam = boto3.client("iam")
    results = []

    try:
        # ─── Check 1: Root account MFA ────────────────────────────
        account_summary = iam.get_account_summary()["SummaryMap"]

        root_info = {
            "resource_type": "IAM",
            "resource_id": "root-account",
            "name": "Root Account",
            "issues": [],
            "details": {}
        }

        if account_summary.get("AccountMFAEnabled", 0) == 0:
            root_info["issues"].append({
                "severity": "CRITICAL",
                "check": "Root MFA",
                "problem": "Root account does not have MFA enabled",
                "impact": "If root credentials are compromised, attacker has full AWS access",
                "fix": "Enable MFA on root account immediately via IAM Console → Security credentials"
            })
        else:
            root_info["details"]["mfa_enabled"] = True

        root_info["health"] = "CRITICAL" if root_info["issues"] else "HEALTHY"
        results.append(root_info)

        # ─── Check 2: IAM Users with old access keys ───────────────
        users = iam.list_users()["Users"]

        for user in users:
            username = user["UserName"]

            user_info = {
                "resource_type": "IAM",
                "resource_id": username,
                "name": f"IAM User: {username}",
                "issues": [],
                "details": {
                    "created": str(user.get("CreateDate"))
                }
            }

            # Check access keys
            keys = iam.list_access_keys(UserName=username)["AccessKeyMetadata"]
            for key in keys:
                key_id = key["AccessKeyId"]
                created = key["CreateDate"]
                status = key["Status"]

                # Calculate age in days
                age_days = (datetime.now(timezone.utc) - created).days
                user_info["details"][f"key_{key_id}_age_days"] = age_days
                user_info["details"][f"key_{key_id}_status"] = status

                if age_days > 90 and status == "Active":
                    user_info["issues"].append({
                        "severity": "WARNING",
                        "check": "Old Access Key",
                        "problem": f"Access key {key_id} is {age_days} days old",
                        "impact": "Old keys are security risk - should be rotated regularly",
                        "fix": f"Rotate access key for user {username}: create new key, update applications, delete old key"
                    })

                if status == "Inactive":
                    user_info["issues"].append({
                        "severity": "INFO",
                        "check": "Inactive Key",
                        "problem": f"Access key {key_id} is inactive",
                        "impact": "Unused inactive keys are unnecessary security risk",
                        "fix": f"Delete inactive access key {key_id} for user {username}"
                    })

            # Check MFA for users
            mfa_devices = iam.list_mfa_devices(UserName=username)["MFADevices"]
            if not mfa_devices:
                user_info["issues"].append({
                    "severity": "WARNING",
                    "check": "User MFA",
                    "problem": f"IAM user {username} has no MFA device",
                    "impact": "Account vulnerable if password is compromised",
                    "fix": f"Enable MFA for user {username} in IAM console"
                })

            user_info["health"] = (
                "CRITICAL" if any(i["severity"] == "CRITICAL" for i in user_info["issues"])
                else "WARNING" if any(i["severity"] == "WARNING" for i in user_info["issues"])
                else "INFO" if user_info["issues"]
                else "HEALTHY"
            )
            results.append(user_info)

    except Exception as e:
        results.append({
            "resource_type": "IAM",
            "resource_id": "SCAN_ERROR",
            "error": str(e),
            "health": "ERROR"
        })

    return results