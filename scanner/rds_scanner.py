import boto3


def scan_rds(region="us-east-1") -> list:
    """
    Scans RDS instances for connectivity and config issues
    """
    rds = boto3.client("rds", region_name=region)
    results = []

    try:
        response = rds.describe_db_instances()

        for db in response["DBInstances"]:
            db_id = db["DBInstanceIdentifier"]
            engine = db["Engine"]
            status = db["DBInstanceStatus"]

            db_port = db.get("Endpoint", {}).get("Port", 3306)

            db_info = {
                "resource_type": "RDS",
                "resource_id": db_id,
                "name": db_id,
                "engine": engine,
                "status": status,
                "issues": [],
                "details": {
                    "engine": engine,
                    "status": status,
                    "port": db_port,
                    "instance_class": db.get("DBInstanceClass"),
                    "storage": db.get("AllocatedStorage"),
                    "multi_az": db.get("MultiAZ", False)
                }
            }

            # ─── Check 1: Publicly accessible ─────────────────────
            is_public = db.get("PubliclyAccessible", False)
            db_info["details"]["publicly_accessible"] = is_public

            if is_public:
                db_info["issues"].append({
                    "severity": "WARNING",
                    "check": "Public Access",
                    "problem": "RDS instance is publicly accessible",
                    "impact": "Database exposed to internet - security risk",
                    "fix": "Disable 'Publicly accessible' in RDS settings unless absolutely required. Use VPC/security groups to control access"
                })

            # ─── Check 2: Security Group port check ───────────────
            vpc_sg_ids = [sg["VpcSecurityGroupId"] for sg in db.get("VpcSecurityGroups", [])]
            db_info["details"]["security_groups"] = vpc_sg_ids

            if vpc_sg_ids:
                ec2 = boto3.client("ec2", region_name=region)
                sg_response = ec2.describe_security_groups(GroupIds=vpc_sg_ids)

                db_port_allowed = False
                for sg in sg_response["SecurityGroups"]:
                    for rule in sg.get("IpPermissions", []):
                        from_port = rule.get("FromPort", 0)
                        to_port = rule.get("ToPort", 0)
                        if from_port <= db_port <= to_port:
                            db_port_allowed = True

                if not db_port_allowed:
                    db_info["issues"].append({
                        "severity": "CRITICAL",
                        "check": "Database Port",
                        "problem": f"Port {db_port} ({engine}) not open in security group",
                        "impact": "Applications cannot connect to database",
                        "fix": f"Add inbound rule: Port {db_port}, Source = application server security group or private IP range"
                    })

            # ─── Check 3: Backup ──────────────────────────────────
            backup_retention = db.get("BackupRetentionPeriod", 0)
            db_info["details"]["backup_retention_days"] = backup_retention

            if backup_retention == 0:
                db_info["issues"].append({
                    "severity": "CRITICAL",
                    "check": "Backup",
                    "problem": "Automated backups are DISABLED (retention = 0)",
                    "impact": "Cannot recover database if data is lost",
                    "fix": "Set backup retention period to at least 7 days in RDS settings"
                })
            elif backup_retention < 7:
                db_info["issues"].append({
                    "severity": "WARNING",
                    "check": "Backup",
                    "problem": f"Backup retention is only {backup_retention} days",
                    "impact": "Limited recovery window",
                    "fix": "Increase backup retention to at least 7 days"
                })

            # ─── Check 4: Multi-AZ ────────────────────────────────
            if not db.get("MultiAZ", False):
                db_info["issues"].append({
                    "severity": "INFO",
                    "check": "High Availability",
                    "problem": "Multi-AZ not enabled",
                    "impact": "No automatic failover if the AZ goes down",
                    "fix": "Enable Multi-AZ for production databases"
                })

            # ─── Check 5: Storage encryption ──────────────────────
            if not db.get("StorageEncrypted", False):
                db_info["issues"].append({
                    "severity": "WARNING",
                    "check": "Encryption",
                    "problem": "Storage encryption not enabled",
                    "impact": "Data at rest is not encrypted",
                    "fix": "Create an encrypted snapshot and restore to a new encrypted instance"
                })

            # Overall health
            if not db_info["issues"]:
                db_info["health"] = "HEALTHY"
            elif any(i["severity"] == "CRITICAL" for i in db_info["issues"]):
                db_info["health"] = "CRITICAL"
            elif any(i["severity"] == "WARNING" for i in db_info["issues"]):
                db_info["health"] = "WARNING"
            else:
                db_info["health"] = "INFO"

            results.append(db_info)

    except Exception as e:
        results.append({
            "resource_type": "RDS",
            "resource_id": "SCAN_ERROR",
            "error": str(e),
            "health": "ERROR"
        })

    return results