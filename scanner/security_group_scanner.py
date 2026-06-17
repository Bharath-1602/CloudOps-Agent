import boto3


def scan_security_groups(region="us-east-1") -> list:
    """
    Scans security groups for dangerous rules
    """
    ec2 = boto3.client("ec2", region_name=region)
    results = []

    try:
        response = ec2.describe_security_groups()

        for sg in response["SecurityGroups"]:
            sg_id = sg["GroupId"]
            sg_name = sg.get("GroupName", "unnamed")

            sg_info = {
                "resource_type": "SecurityGroup",
                "resource_id": sg_id,
                "name": sg_name,
                "issues": [],
                "details": {
                    "description": sg.get("Description"),
                    "vpc_id": sg.get("VpcId")
                }
            }

            # ─── Check 1: Wide open inbound rules ─────────────────
            dangerous_ports = {
                22: "SSH",
                3389: "RDP",
                3306: "MySQL",
                5432: "PostgreSQL",
                27017: "MongoDB",
                6379: "Redis",
                9200: "Elasticsearch"
            }

            for rule in sg.get("IpPermissions", []):
                from_port = rule.get("FromPort", 0)
                to_port = rule.get("ToPort", 65535)
                protocol = rule.get("IpProtocol", "-1")

                # Check for 0.0.0.0/0
                open_to_world = any(
                    cidr.get("CidrIp") == "0.0.0.0/0"
                    for cidr in rule.get("IpRanges", [])
                )

                if open_to_world:
                    # All traffic open
                    if protocol == "-1":
                        sg_info["issues"].append({
                            "severity": "CRITICAL",
                            "check": "All Traffic Open",
                            "problem": "ALL inbound traffic allowed from 0.0.0.0/0",
                            "impact": "Completely exposed to internet - extreme security risk",
                            "fix": "Remove this rule immediately and add specific rules only for required ports"
                        })

                    # Check dangerous ports
                    for port, service in dangerous_ports.items():
                        if from_port <= port <= to_port:
                            sg_info["issues"].append({
                                "severity": "CRITICAL",
                                "check": f"{service} Exposed",
                                "problem": f"Port {port} ({service}) open to entire internet (0.0.0.0/0)",
                                "impact": f"{service} accessible from anywhere - brute force risk",
                                "fix": f"Restrict port {port} to specific IP addresses only"
                            })

            # ─── Check 2: Wide open outbound ──────────────────────
            for rule in sg.get("IpPermissionsEgress", []):
                protocol = rule.get("IpProtocol", "-1")
                open_to_world = any(
                    cidr.get("CidrIp") == "0.0.0.0/0"
                    for cidr in rule.get("IpRanges", [])
                )
                if open_to_world and protocol == "-1":
                    sg_info["issues"].append({
                        "severity": "INFO",
                        "check": "Outbound Traffic",
                        "problem": "All outbound traffic allowed (common but worth reviewing)",
                        "impact": "Potential data exfiltration if instance is compromised",
                        "fix": "Consider restricting outbound to only required ports/destinations"
                    })
                    break  # Only flag once

            # Overall health
            if not sg_info["issues"]:
                sg_info["health"] = "HEALTHY"
            elif any(i["severity"] == "CRITICAL" for i in sg_info["issues"]):
                sg_info["health"] = "CRITICAL"
            elif any(i["severity"] == "WARNING" for i in sg_info["issues"]):
                sg_info["health"] = "WARNING"
            else:
                sg_info["health"] = "INFO"

            results.append(sg_info)

    except Exception as e:
        results.append({
            "resource_type": "SecurityGroup",
            "resource_id": "SCAN_ERROR",
            "error": str(e),
            "health": "ERROR"
        })

    return results