import boto3


def scan_ec2(region="us-east-1") -> list:
    """
    Scans all EC2 instances and detects issues
    """
    ec2 = boto3.client("ec2", region_name=region)
    issues = []

    try:
        response = ec2.describe_instances()

        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:

                instance_id = instance["InstanceId"]
                state = instance["State"]["Name"]

                # Get name tag
                name = "Unnamed"
                for tag in instance.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]

                instance_info = {
                    "resource_type": "EC2",
                    "resource_id": instance_id,
                    "name": name,
                    "state": state,
                    "instance_type": instance.get("InstanceType", "unknown"),
                    "region": region,
                    "issues": [],
                    "details": {}
                }

                # Skip terminated instances
                if state == "terminated":
                    continue

                # ─── Check 1: Public IP ───────────────────────────
                public_ip = instance.get("PublicIpAddress")
                private_ip = instance.get("PrivateIpAddress")

                instance_info["details"]["public_ip"] = public_ip or "None"
                instance_info["details"]["private_ip"] = private_ip or "None"

                if not public_ip:
                    instance_info["issues"].append({
                        "severity": "CRITICAL",
                        "check": "SSH Access",
                        "problem": "No Public IP address assigned",
                        "impact": "Cannot SSH into this instance from internet",
                        "fix": "Allocate an Elastic IP and associate it with this instance, OR use AWS Systems Manager Session Manager (recommended - no public IP needed)"
                    })

                # ─── Check 2: Security Groups ─────────────────────
                sg_ids = [sg["GroupId"] for sg in instance.get("SecurityGroups", [])]
                instance_info["details"]["security_groups"] = sg_ids

                if sg_ids:
                    sg_client = boto3.client("ec2", region_name=region)
                    sg_response = sg_client.describe_security_groups(GroupIds=sg_ids)

                    port_22_allowed = False
                    port_80_allowed = False
                    port_443_allowed = False
                    wide_open_ports = []

                    for sg in sg_response["SecurityGroups"]:
                        for rule in sg.get("IpPermissions", []):
                            from_port = rule.get("FromPort", 0)
                            to_port = rule.get("ToPort", 65535)

                            # Check port 22
                            if from_port <= 22 <= to_port:
                                for cidr in rule.get("IpRanges", []):
                                    if cidr.get("CidrIp") == "0.0.0.0/0":
                                        port_22_allowed = True
                                        wide_open_ports.append(22)

                            # Check port 80
                            if from_port <= 80 <= to_port:
                                port_80_allowed = True

                            # Check port 443
                            if from_port <= 443 <= to_port:
                                port_443_allowed = True

                    if not port_22_allowed and state == "running":
                        instance_info["issues"].append({
                            "severity": "CRITICAL",
                            "check": "SSH Port",
                            "problem": "Port 22 not open in security group",
                            "impact": "SSH connections will be rejected even if instance has public IP",
                            "fix": "Add inbound rule: Type=SSH, Port=22, Source=Your IP/32 in the security group"
                        })

                    if not port_80_allowed and not port_443_allowed:
                        instance_info["issues"].append({
                            "severity": "WARNING",
                            "check": "Web Traffic",
                            "problem": "Ports 80 and 443 not open",
                            "impact": "If this is a web server, HTTP/HTTPS traffic is blocked",
                            "fix": "Add inbound rules for port 80 (HTTP) and 443 (HTTPS) if this is a web server"
                        })

                    if 22 in wide_open_ports:
                        instance_info["issues"].append({
                            "severity": "WARNING",
                            "check": "Security Best Practice",
                            "problem": "Port 22 open to 0.0.0.0/0 (entire internet)",
                            "impact": "Instance exposed to SSH brute force attacks",
                            "fix": "Restrict SSH to your specific IP: Source = YOUR_IP/32"
                        })

                # ─── Check 3: Key Pair ────────────────────────────
                key_name = instance.get("KeyName")
                instance_info["details"]["key_pair"] = key_name or "None"

                if not key_name:
                    instance_info["issues"].append({
                        "severity": "WARNING",
                        "check": "Key Pair",
                        "problem": "No key pair associated with instance",
                        "impact": "Cannot SSH without key pair",
                        "fix": "Key pair must be assigned at launch. Consider using SSM Session Manager instead"
                    })

                # ─── Check 4: Instance stopped ────────────────────
                if state == "stopped":
                    instance_info["issues"].append({
                        "severity": "INFO",
                        "check": "Instance State",
                        "problem": "Instance is stopped",
                        "impact": "Instance is not running",
                        "fix": "Start the instance from EC2 console or run: aws ec2 start-instances --instance-ids " + instance_id
                    })

                # ─── Determine overall health ─────────────────────
                if not instance_info["issues"]:
                    instance_info["health"] = "HEALTHY"
                elif any(i["severity"] == "CRITICAL" for i in instance_info["issues"]):
                    instance_info["health"] = "CRITICAL"
                elif any(i["severity"] == "WARNING" for i in instance_info["issues"]):
                    instance_info["health"] = "WARNING"
                else:
                    instance_info["health"] = "INFO"

                issues.append(instance_info)

    except Exception as e:
        issues.append({
            "resource_type": "EC2",
            "resource_id": "SCAN_ERROR",
            "error": str(e),
            "health": "ERROR"
        })

    return issues