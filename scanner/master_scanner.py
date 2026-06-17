import concurrent.futures
import time
from scanner.ec2_scanner import scan_ec2
from scanner.s3_scanner import scan_s3
from scanner.rds_scanner import scan_rds
from scanner.lambda_scanner import scan_lambda
from scanner.security_group_scanner import scan_security_groups
from scanner.iam_scanner import scan_iam


def run_full_scan(region: str = "us-east-1", progress_callback=None) -> dict:
    """
    Runs all scanners in parallel and returns combined results
    progress_callback: function(message) to update UI
    """
    start_time = time.time()

    def update(msg):
        if progress_callback:
            progress_callback(msg)

    update("🔍 Starting EC2 scan...")
    update("🔍 Starting S3 scan...")
    update("🔍 Starting RDS scan...")
    update("🔍 Starting Lambda scan...")
    update("🔍 Starting Security Group scan...")
    update("🔍 Starting IAM scan...")

    # Run scans in parallel for speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        future_ec2 = executor.submit(scan_ec2, region)
        future_s3 = executor.submit(scan_s3)
        future_rds = executor.submit(scan_rds, region)
        future_lambda = executor.submit(scan_lambda, region)
        future_sg = executor.submit(scan_security_groups, region)
        future_iam = executor.submit(scan_iam)

        ec2_results = future_ec2.result()
        s3_results = future_s3.result()
        rds_results = future_rds.result()
        lambda_results = future_lambda.result()
        sg_results = future_sg.result()
        iam_results = future_iam.result()

    update("✅ All scans complete! Generating AI analysis...")

    # Combine all results
    all_resources = (
        ec2_results + s3_results + rds_results +
        lambda_results + sg_results + iam_results
    )

    # Summary statistics
    total = len(all_resources)
    critical_count = sum(1 for r in all_resources if r.get("health") == "CRITICAL")
    warning_count = sum(1 for r in all_resources if r.get("health") == "WARNING")
    healthy_count = sum(1 for r in all_resources if r.get("health") == "HEALTHY")
    info_count = sum(1 for r in all_resources if r.get("health") == "INFO")

    scan_time = round(time.time() - start_time, 2)

    return {
        "scan_metadata": {
            "region": region,
            "scan_time_seconds": scan_time,
            "total_resources": total,
            "summary": {
                "critical": critical_count,
                "warning": warning_count,
                "info": info_count,
                "healthy": healthy_count
            }
        },
        "resources": {
            "ec2": ec2_results,
            "s3": s3_results,
            "rds": rds_results,
            "lambda": lambda_results,
            "security_groups": sg_results,
            "iam": iam_results
        }
    }