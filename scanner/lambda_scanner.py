import boto3


def scan_lambda(region="us-east-1") -> list:
    """
    Scans Lambda functions for misconfigurations
    """
    client = boto3.client("lambda", region_name=region)
    results = []

    try:
        paginator = client.get_paginator("list_functions")
        functions = []
        for page in paginator.paginate():
            functions.extend(page["Functions"])

        for fn in functions:
            fn_name = fn["FunctionName"]

            fn_info = {
                "resource_type": "Lambda",
                "resource_id": fn_name,
                "name": fn_name,
                "issues": [],
                "details": {
                    "runtime": fn.get("Runtime", "unknown"),
                    "timeout": fn.get("Timeout", 3),
                    "memory": fn.get("MemorySize", 128),
                    "last_modified": fn.get("LastModified"),
                    "role": fn.get("Role")
                }
            }

            # ─── Check 1: Timeout too low ──────────────────────────
            timeout = fn.get("Timeout", 3)
            if timeout <= 3:
                fn_info["issues"].append({
                    "severity": "WARNING",
                    "check": "Timeout",
                    "problem": f"Timeout is only {timeout} seconds",
                    "impact": "Function may timeout before completing its work",
                    "fix": "Increase timeout based on expected execution time (max 15 minutes)"
                })

            # ─── Check 2: Memory too low ───────────────────────────
            memory = fn.get("MemorySize", 128)
            if memory < 256:
                fn_info["issues"].append({
                    "severity": "INFO",
                    "check": "Memory",
                    "problem": f"Memory is only {memory}MB",
                    "impact": "Function may run slow or run out of memory",
                    "fix": "Increase memory allocation (more memory also gives more CPU)"
                })

            # ─── Check 3: VPC check (if in VPC, check internet) ───
            vpc_config = fn.get("VpcConfig", {})
            subnet_ids = vpc_config.get("SubnetIds", [])
            if subnet_ids:
                fn_info["details"]["in_vpc"] = True
                fn_info["details"]["subnets"] = subnet_ids
                fn_info["issues"].append({
                    "severity": "INFO",
                    "check": "VPC Configuration",
                    "problem": "Function is inside a VPC",
                    "impact": "Function cannot reach internet unless NAT Gateway is configured",
                    "fix": "Ensure NAT Gateway exists in VPC if function needs internet access"
                })
            else:
                fn_info["details"]["in_vpc"] = False

            # ─── Check 4: Deprecated runtime ──────────────────────
            runtime = fn.get("Runtime", "")
            deprecated_runtimes = [
                "nodejs12.x", "nodejs10.x", "nodejs8.10",
                "python2.7", "python3.6", "python3.7",
                "ruby2.5", "java8", "dotnetcore2.1", "dotnetcore3.1"
            ]
            if runtime in deprecated_runtimes:
                fn_info["issues"].append({
                    "severity": "CRITICAL",
                    "check": "Runtime",
                    "problem": f"Runtime '{runtime}' is deprecated",
                    "impact": "Function may stop working, security vulnerabilities",
                    "fix": f"Upgrade to a supported runtime version"
                })

            # Overall health
            if not fn_info["issues"]:
                fn_info["health"] = "HEALTHY"
            elif any(i["severity"] == "CRITICAL" for i in fn_info["issues"]):
                fn_info["health"] = "CRITICAL"
            elif any(i["severity"] == "WARNING" for i in fn_info["issues"]):
                fn_info["health"] = "WARNING"
            else:
                fn_info["health"] = "INFO"

            results.append(fn_info)

    except Exception as e:
        results.append({
            "resource_type": "Lambda",
            "resource_id": "SCAN_ERROR",
            "error": str(e),
            "health": "ERROR"
        })

    return results