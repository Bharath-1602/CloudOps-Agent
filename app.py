import streamlit as st
import time
import plotly.graph_objects as go
import pandas as pd
from agent.core_agent import CloudOpsAgent
from scanner.master_scanner import run_full_scan
from utils.report_generator import generate_text_report

# ─── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="CloudOps AI Agent",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS Styling ──────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF9900;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #888;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-critical { background: #ff4444; color: white; padding: 10px; border-radius: 8px; text-align: center; }
    .metric-warning  { background: #ff8800; color: white; padding: 10px; border-radius: 8px; text-align: center; }
    .metric-healthy  { background: #00aa44; color: white; padding: 10px; border-radius: 8px; text-align: center; }
    .metric-info     { background: #0088cc; color: white; padding: 10px; border-radius: 8px; text-align: center; }
    .chat-message-user { background: #2d2d2d; padding: 10px 15px; border-radius: 10px; margin: 5px 0; }
    .chat-message-ai   { background: #1a3a5c; padding: 10px 15px; border-radius: 10px; margin: 5px 0; }
    .issue-critical { border-left: 4px solid #ff4444; padding-left: 10px; margin: 5px 0; }
    .issue-warning  { border-left: 4px solid #ff8800; padding-left: 10px; margin: 5px 0; }
    .issue-info     { border-left: 4px solid #0088cc; padding-left: 10px; margin: 5px 0; }
</style>
""", unsafe_allow_html=True)

# ─── Initialize Session State ──────────────────────────────────
if "agent" not in st.session_state:
    st.session_state.agent = CloudOpsAgent()

if "scan_results" not in st.session_state:
    st.session_state.scan_results = None

if "ai_analysis" not in st.session_state:
    st.session_state.ai_analysis = None

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "scan_done" not in st.session_state:
    st.session_state.scan_done = False

# ─── Header ───────────────────────────────────────────────────
st.markdown('<div class="main-header">☁️ CloudOps AI Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Intelligent AWS Cloud Troubleshooter — Powered by Amazon Bedrock Nova</div>', unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/9/93/Amazon_Web_Services_Logo.svg", width=100)
    st.markdown("### ⚙️ Configuration")

    region = st.selectbox(
        "AWS Region",
        ["us-east-1", "us-east-2", "us-west-1", "us-west-2",
         "eu-west-1", "eu-central-1", "ap-south-1", "ap-southeast-1"],
        index=0
    )

    st.markdown("---")
    st.markdown("### 📊 Scan Controls")

    scan_button = st.button(
        "🔍 Start Full AWS Scan",
        type="primary",
        use_container_width=True
    )

    if st.session_state.scan_done:
        if st.button("🗑️ Clear & Rescan", use_container_width=True):
            st.session_state.scan_results = None
            st.session_state.ai_analysis = None
            st.session_state.chat_messages = []
            st.session_state.scan_done = False
            st.session_state.agent.clear_history()
            st.rerun()

    st.markdown("---")
    st.markdown("### 📁 Resources Scanned")
    st.markdown("""
    - 🖥️ EC2 Instances
    - 🗄️ RDS Databases
    - 🪣 S3 Buckets
    - ⚡ Lambda Functions
    - 🔒 Security Groups
    - 👤 IAM Users & Root
    """)

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("Powered by **Amazon Bedrock Nova** via IAM Role")

# ─── MAIN AREA ────────────────────────────────────────────────

# ─── Scan Execution ───────────────────────────────────────────
if scan_button and not st.session_state.scan_done:
    st.markdown("## 🔍 Scanning Your AWS Account...")

    progress_bar = st.progress(0)
    status_text = st.empty()
    log_area = st.empty()

    logs = []

    def update_progress(msg):
        logs.append(msg)
        log_area.code("\n".join(logs))

    # Simulate progress during scan
    with st.spinner("Scanning resources in parallel..."):
        progress_bar.progress(10)
        status_text.text("Connecting to AWS...")
        time.sleep(0.5)

        progress_bar.progress(30)
        status_text.text("Scanning EC2, RDS, S3, Lambda, IAM, Security Groups...")

        results = run_full_scan(
            region=region,
            progress_callback=update_progress
        )

        progress_bar.progress(80)
        status_text.text("Running AI Analysis via Amazon Bedrock...")

        # AI Analysis
        ai_analysis = st.session_state.agent.analyze_scan(results)

        progress_bar.progress(100)
        status_text.text("✅ Done!")

    st.session_state.scan_results = results
    st.session_state.ai_analysis = ai_analysis
    st.session_state.scan_done = True
    time.sleep(1)
    st.rerun()

# ─── Display Results ───────────────────────────────────────────
if st.session_state.scan_done and st.session_state.scan_results:
    results = st.session_state.scan_results
    meta = results["scan_metadata"]
    summary = meta["summary"]
    resources = results["resources"]

    # ── Summary Metrics ──────────────────────────────────────
    st.markdown("## 📊 Scan Summary")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Resources", meta["total_resources"])
    with col2:
        st.metric("🔴 Critical", summary["critical"])
    with col3:
        st.metric("🟡 Warning", summary["warning"])
    with col4:
        st.metric("🔵 Info", summary["info"])
    with col5:
        st.metric("🟢 Healthy", summary["healthy"])

    st.caption(f"⏱️ Scan completed in {meta['scan_time_seconds']} seconds | Region: {meta['region']}")

    # ── Donut Chart ───────────────────────────────────────────
    col_chart, col_bar = st.columns(2)

    with col_chart:
        fig = go.Figure(data=[go.Pie(
            labels=["Critical", "Warning", "Info", "Healthy"],
            values=[
                summary["critical"],
                summary["warning"],
                summary["info"],
                summary["healthy"]
            ],
            hole=0.5,
            marker_colors=["#ff4444", "#ff8800", "#0088cc", "#00aa44"]
        )])
        fig.update_layout(
            title="Health Distribution",
            showlegend=True,
            height=300,
            margin=dict(t=40, b=0, l=0, r=0)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_bar:
        resource_counts = {}
        for rtype, rlist in resources.items():
            resource_counts[rtype.upper()] = len(rlist)

        fig2 = go.Figure(data=[go.Bar(
            x=list(resource_counts.keys()),
            y=list(resource_counts.values()),
            marker_color="#FF9900"
        )])
        fig2.update_layout(
            title="Resources by Type",
            height=300,
            margin=dict(t=40, b=0, l=0, r=0)
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── Tabs for different views ──────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🤖 AI Analysis",
        "📋 Resource Details",
        "💬 Chat with Agent",
        "📥 Export Report"
    ])

    # ── TAB 1: AI Analysis ────────────────────────────────────
    with tab1:
        st.markdown("## 🤖 Amazon Bedrock Nova Analysis")
        st.markdown(
            f'<div style="background:#1a1a2e; padding:20px; border-radius:10px; '
            f'border-left:4px solid #FF9900; line-height:1.8;">'
            f'{st.session_state.ai_analysis.replace(chr(10), "<br>")}'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── TAB 2: Resource Details ───────────────────────────────
    with tab2:
        st.markdown("## 📋 Detailed Resource Report")

        resource_type_map = {
            "ec2": "🖥️ EC2 Instances",
            "s3": "🪣 S3 Buckets",
            "rds": "🗄️ RDS Databases",
            "lambda": "⚡ Lambda Functions",
            "security_groups": "🔒 Security Groups",
            "iam": "👤 IAM"
        }

        for rtype, label in resource_type_map.items():
            resource_list = resources.get(rtype, [])
            if not resource_list:
                continue

            with st.expander(f"{label} ({len(resource_list)} found)", expanded=True):
                for resource in resource_list:
                    health = resource.get("health", "UNKNOWN")
                    name = resource.get("name", resource.get("resource_id", "unknown"))
                    rid = resource.get("resource_id", "")

                    health_emoji = {
                        "CRITICAL": "🔴",
                        "WARNING": "🟡",
                        "HEALTHY": "🟢",
                        "INFO": "🔵",
                        "ERROR": "⚫"
                    }.get(health, "⚪")

                    # Resource header
                    st.markdown(f"### {health_emoji} {name}")
                    if rid and rid != name:
                        st.caption(f"ID: {rid}")

                    # Details
                    details = resource.get("details", {})
                    if details:
                        detail_cols = st.columns(3)
                        items = list(details.items())
                        for idx, (k, v) in enumerate(items[:6]):
                            with detail_cols[idx % 3]:
                                st.metric(
                                    k.replace("_", " ").title(),
                                    str(v)[:30]
                                )

                    # Issues
                    issues = resource.get("issues", [])
                    if issues:
                        for issue in issues:
                            sev = issue.get("severity", "INFO")
                            color = {
                                "CRITICAL": "#ff4444",
                                "WARNING": "#ff8800",
                                "INFO": "#0088cc"
                            }.get(sev, "#888")

                            st.markdown(
                                f'<div style="border-left:4px solid {color}; '
                                f'padding:10px; margin:5px 0; background:#1a1a2e; border-radius:4px;">'
                                f'<b style="color:{color};">[{sev}] {issue["check"]}</b><br>'
                                f'<b>Problem:</b> {issue["problem"]}<br>'
                                f'<b>Impact:</b> {issue.get("impact", "")}<br>'
                                f'<b>Fix:</b> <code>{issue["fix"]}</code>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                            # Quick Fix button
                            btn_key = f"fix_{rid}_{issue['check']}".replace(" ", "_")
                            if st.button(f"🔧 Get Detailed Fix", key=btn_key):
                                with st.spinner("Getting detailed fix from AI..."):
                                    fix_response = st.session_state.agent.get_quick_fix(
                                        resource=f"{name} ({rid})",
                                        problem=issue["problem"]
                                    )
                                st.info(fix_response)
                    else:
                        st.success("✅ No issues found for this resource")

                    st.markdown("---")

    # ── TAB 3: Chat Interface ─────────────────────────────────
    with tab3:
        st.markdown("## 💬 Chat with CloudOps Agent")
        st.markdown("Ask me anything about your cloud resources, issues, or how to fix them!")

        # Display chat history
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.chat_messages:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant", avatar="☁️"):
                        st.write(message["content"])

        # Quick question buttons
        st.markdown("**Quick Questions:**")
        qcol1, qcol2, qcol3 = st.columns(3)

        with qcol1:
            if st.button("🔴 Show Critical Issues"):
                quick_q = "List all my critical issues and what I should fix first"
                st.session_state.chat_messages.append({"role": "user", "content": quick_q})
                with st.spinner("Thinking..."):
                    response = st.session_state.agent.chat(quick_q)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                st.rerun()

        with qcol2:
            if st.button("🖥️ EC2 SSH Issues"):
                quick_q = "I can't SSH into my EC2 instances. What's wrong and how do I fix it?"
                st.session_state.chat_messages.append({"role": "user", "content": quick_q})
                with st.spinner("Thinking..."):
                    response = st.session_state.agent.chat(quick_q)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                st.rerun()

        with qcol3:
            if st.button("🔒 Security Issues"):
                quick_q = "What are my biggest security vulnerabilities and how do I fix them?"
                st.session_state.chat_messages.append({"role": "user", "content": quick_q})
                with st.spinner("Thinking..."):
                    response = st.session_state.agent.chat(quick_q)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                st.rerun()

        # Chat input
        user_input = st.chat_input("Ask about your cloud resources... e.g. 'Why can't I SSH into my EC2?'")

        if user_input:
            st.session_state.chat_messages.append({"role": "user", "content": user_input})
            with st.spinner("☁️ Agent is thinking..."):
                response = st.session_state.agent.chat(user_input)
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
            st.rerun()

    # ── TAB 4: Export Report ──────────────────────────────────
    with tab4:
        st.markdown("## 📥 Export Scan Report")

        text_report = generate_text_report(results)

        st.text_area(
            "Plain Text Report (copy or download)",
            value=text_report,
            height=400
        )

        st.download_button(
            label="⬇️ Download Report (.txt)",
            data=text_report,
            file_name=f"cloudops_report_{meta['region']}.txt",
            mime="text/plain"
        )

        # Also provide JSON download
        import json
        json_report = json.dumps(results, indent=2, default=str)
        st.download_button(
            label="⬇️ Download Raw Data (.json)",
            data=json_report,
            file_name=f"cloudops_data_{meta['region']}.json",
            mime="application/json"
        )

# ─── Landing Page (before scan) ───────────────────────────────
else:
    if not scan_button:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            ### 🔍 Intelligent Scanning
            Automatically scans all your AWS resources for
            misconfigurations, connectivity issues, and
            security vulnerabilities
            """)

        with col2:
            st.markdown("""
            ### 🤖 AI-Powered Analysis
            Amazon Bedrock Nova analyzes every finding,
            explains what's wrong, why it matters,
            and gives exact fix steps
            """)

        with col3:
            st.markdown("""
            ### 💬 Interactive Chat
            Chat with the AI agent about your specific
            resources. Ask follow-up questions and get
            personalized guidance
            """)

        st.markdown("---")
        st.info("👈 **Click 'Start Full AWS Scan' in the sidebar to begin!**")