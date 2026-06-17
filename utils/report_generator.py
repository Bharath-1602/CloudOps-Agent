def generate_text_report(scan_results: dict) -> str:
    """
    Generates a readable text report from scan results
    """
    meta = scan_results.get("scan_metadata", {})
    summary = meta.get("summary", {})
    resources = scan_results.get("resources", {})

    lines = []
    lines.append("=" * 60)
    lines.append("      CloudOps AI Agent — AWS Scan Report")
    lines.append("=" * 60)
    lines.append(f"Region: {meta.get('region')}")
    lines.append(f"Scan Time: {meta.get('scan_time_seconds')}s")
    lines.append(f"Total Resources: {meta.get('total_resources')}")
    lines.append("")
    lines.append("SUMMARY:")
    lines.append(f"  🔴 CRITICAL : {summary.get('critical', 0)}")
    lines.append(f"  🟡 WARNING  : {summary.get('warning', 0)}")
    lines.append(f"  🔵 INFO     : {summary.get('info', 0)}")
    lines.append(f"  🟢 HEALTHY  : {summary.get('healthy', 0)}")
    lines.append("=" * 60)

    for resource_type, resource_list in resources.items():
        if not resource_list:
            continue

        lines.append(f"\n{'─' * 40}")
        lines.append(f"  {resource_type.upper()} RESOURCES")
        lines.append(f"{'─' * 40}")

        for resource in resource_list:
            health = resource.get("health", "UNKNOWN")
            name = resource.get("name", resource.get("resource_id"))
            emoji = {
                "CRITICAL": "🔴",
                "WARNING": "🟡",
                "HEALTHY": "🟢",
                "INFO": "🔵",
                "ERROR": "⚫"
            }.get(health, "⚪")

            lines.append(f"\n{emoji} {name} [{health}]")

            for issue in resource.get("issues", []):
                lines.append(f"   ⚠ {issue['check']}: {issue['problem']}")
                lines.append(f"     Fix: {issue['fix']}")

            if not resource.get("issues"):
                lines.append(f"   ✓ No issues found")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)