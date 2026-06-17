import streamlit as st
import time
import json
import plotly.graph_objects as go
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
    .chat-message-user {
        background: #2d2d2d;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .chat-message-ai {
        background: #1a3a5c;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
    }
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

if "quick_fix_responses" not in st.session_state:
    st.session_state.quick_fix_responses = {}

# ─── Header ───────────────────────────────────────────────────
st.markdown('<div class="main-header">☁️ CloudOps AI Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Intelligent AWS Cloud Troubleshooter '
    '— Powered by Amazon Bedrock Nova</div>',
    unsafe_allow_html=True
)

# ─── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    region = st.selectbox(
        "AWS Region",
        [
            "us-east-1", "us-east-2", "us-west-1", "us-west-2",
            "eu-west-1", "eu-central-1", "ap-south-1", "ap-southeast-1"
        ],
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
            st.session_state.quick_fix_responses = {}
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

# ─── SCAN EXECUTION ───────────────────────────────────────────
if scan_button and not st.session_state.scan_done:
    st.markdown("## 🔍 Scanning Your AWS Account...")

    progress_bar = st.progress(0)
    status_text  = st.empty()
    log_area     = st.empty()

    logs = []

    def update_progress(msg):
        logs.append(msg)
        log_area.code("\n".join(logs))

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
        status_text.text("Running AI Analysis via Amazon Bedrock Nova...")

        ai_analysis = st.session_state.agent.analyze_scan(results)

        progress_bar.progress(100)
        status_text.text("✅ Scan Complete!")

    st.session_state.scan_results  = results
    st.session_state.ai_analysis   = ai_analysis
    st.session_state.scan_done     = True
    time.sleep(1)
    st.rerun()

# ─── RESULTS DISPLAY ──────────────────────────────────────────
if st.session_state.scan_done and st.session_state.scan_results:

    results   = st.session_state.scan_results
    meta      = results["scan_metadata"]
    summary   = meta["summary"]
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

    st.caption(
        f"⏱️ Scan completed in {meta['scan_time_seconds']} seconds "
        f"| Region: {meta['region']}"
    )

    # ── Charts ────────────────────────────────────────────────
    col_chart, col_bar = st.columns(2)

    with col_chart:
        fig_donut = go.Figure(data=[go.Pie(
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
        fig_donut.update_layout(
            title="Health Distribution",
            showlegend=True,
            height=300,
            margin=dict(t=40, b=0, l=0, r=0)
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_bar:
        resource_counts = {
            rtype.upper(): len(rlist)
            for rtype, rlist in resources.items()
            if rlist
        }
        fig_bar = go.Figure(data=[go.Bar(
            x=list(resource_counts.keys()),
            y=list(resource_counts.values()),
            marker_color="#FF9900"
        )])
        fig_bar.update_layout(
            title="Resources by Type",
            height=300,
            margin=dict(t=40, b=0, l=0, r=0)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🤖 AI Analysis",
        "📋 Resource Details",
        "💬 Chat with Agent",
        "📥 Export Report"
    ])

    # ══════════════════════════════════════════════════════════
    # TAB 1 — AI Analysis
    # ══════════════════════════════════════════════════════════
    with tab1:
        st.markdown("## 🤖 Amazon Bedrock Nova Analysis")

        if st.session_state.ai_analysis:
            st.markdown(
                f'<div style="background:#1a1a2e; padding:20px; border-radius:10px; '
                f'border-left:4px solid #FF9900; line-height:1.8;">'
                f'{st.session_state.ai_analysis.replace(chr(10), "<br>")}'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.warning("No AI analysis available. Please rescan.")

    # ══════════════════════════════════════════════════════════
    # TAB 2 — Resource Details
    # ══════════════════════════════════════════════════════════
    with tab2:
        st.markdown("## 📋 Detailed Resource Report")

        resource_type_map = {
            "ec2":             "🖥️ EC2 Instances",
            "s3":              "🪣 S3 Buckets",
            "rds":             "🗄️ RDS Databases",
            "lambda":          "⚡ Lambda Functions",
            "security_groups": "🔒 Security Groups",
            "iam":             "👤 IAM"
        }

        # Health emoji helper
        def health_emoji(h):
            return {
                "CRITICAL": "🔴",
                "WARNING":  "🟡",
                "HEALTHY":  "🟢",
                "INFO":     "🔵",
                "ERROR":    "⚫"
            }.get(h, "⚪")

        # Severity color helper
        def sev_color(s):
            return {
                "CRITICAL": "#ff4444",
                "WARNING":  "#ff8800",
                "INFO":     "#0088cc"
            }.get(s, "#888888")

        for rtype, label in resource_type_map.items():
            resource_list = resources.get(rtype, [])
            if not resource_list:
                continue

            with st.expander(f"{label} ({len(resource_list)} found)", expanded=True):

                for resource in resource_list:
                    health = resource.get("health", "UNKNOWN")
                    name   = resource.get("name", resource.get("resource_id", "unknown"))
                    rid    = resource.get("resource_id", "unknown")

                    st.markdown(f"### {health_emoji(health)} {name}")

                    if rid and rid != name:
                        st.caption(f"ID: {rid}")

                    # ── Resource Details Grid ──────────────────
                    details = resource.get("details", {})
                    if details:
                        items = list(details.items())[:6]
                        detail_cols = st.columns(3)
                        for idx, (k, v) in enumerate(items):
                            with detail_cols[idx % 3]:
                                st.metric(
                                    k.replace("_", " ").title(),
                                    str(v)[:30]
                                )

                    # ── Issues ────────────────────────────────
                    issues = resource.get("issues", [])

                    if issues:
                        for issue_idx, issue in enumerate(issues):
                            sev   = issue.get("severity", "INFO")
                            color = sev_color(sev)

                            # Issue card
                            st.markdown(
                                f'<div style="border-left:4px solid {color}; '
                                f'padding:10px; margin:8px 0; '
                                f'background:#1a1a2e; border-radius:4px;">'
                                f'<b style="color:{color};">[{sev}] {issue["check"]}</b><br>'
                                f'<b>Problem:</b> {issue["problem"]}<br>'
                                f'<b>Impact:</b> {issue.get("impact", "N/A")}<br>'
                                f'<b>Fix:</b> <code>{issue["fix"]}</code>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                            # ── Unique button key ──────────────
                            # Combines: resource_type + resource_id +
                            #           check_name + issue_index
                            # Cleans special characters that break keys
                            raw_key = (
                                f"fix_{rtype}_{rid}_"
                                f"{issue['check']}_{issue_idx}"
                            )
                            btn_key = (
                                raw_key
                                .replace(" ", "_")
                                .replace("/", "_")
                                .replace(":", "_")
                                .replace(".", "_")
                                .replace("-", "_")
                                .replace("(", "_")
                                .replace(")", "_")
                            )

                            # Quick Fix Button
                            if st.button(
                                f"🔧 Get Detailed Fix for: {issue['check']}",
                                key=btn_key
                            ):
                                with st.spinner(
                                    f"Getting detailed fix from Amazon Bedrock Nova..."
                                ):
                                    fix_response = st.session_state.agent.get_quick_fix(
                                        resource=f"{name} ({rid})",
                                        problem=issue["problem"]
                                    )
                                # Store response in session state so it persists
                                st.session_state.quick_fix_responses[btn_key] = fix_response

                            # Show stored fix response if it exists
                            if btn_key in st.session_state.quick_fix_responses:
                                st.info(
                                    st.session_state.quick_fix_responses[btn_key]
                                )

                    else:
                        st.success("✅ No issues found for this resource")

                    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # TAB 3 — Chat Interface
    # ══════════════════════════════════════════════════════════
    with tab3:
        st.markdown("## 💬 Chat with CloudOps Agent")
        st.markdown(
            "Ask me anything about your cloud resources, "
            "issues, or how to fix them!"
        )

        # ── Display Chat History ───────────────────────────
        for message in st.session_state.chat_messages:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant", avatar="☁️"):
                    st.write(message["content"])

        # ── Quick Question Buttons ─────────────────────────
        st.markdown("**⚡ Quick Questions:**")
        qcol1, qcol2, qcol3 = st.columns(3)

        with qcol1:
            if st.button(
                "🔴 Show Critical Issues",
                key="quick_btn_critical",
                use_container_width=True
            ):
                quick_q = (
                    "List all my critical issues and "
                    "what I should fix first"
                )
                st.session_state.chat_messages.append(
                    {"role": "user", "content": quick_q}
                )
                with st.spinner("Thinking..."):
                    response = st.session_state.agent.chat(quick_q)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": response}
                )
                st.rerun()

        with qcol2:
            if st.button(
                "🖥️ EC2 SSH Issues",
                key="quick_btn_ssh",
                use_container_width=True
            ):
                quick_q = (
                    "I can't SSH into my EC2 instances. "
                    "What's wrong and how do I fix it?"
                )
                st.session_state.chat_messages.append(
                    {"role": "user", "content": quick_q}
                )
                with st.spinner("Thinking..."):
                    response = st.session_state.agent.chat(quick_q)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": response}
                )
                st.rerun()

        with qcol3:
            if st.button(
                "🔒 Security Issues",
                key="quick_btn_security",
                use_container_width=True
            ):
                quick_q = (
                    "What are my biggest security vulnerabilities "
                    "and how do I fix them?"
                )
                st.session_state.chat_messages.append(
                    {"role": "user", "content": quick_q}
                )
                with st.spinner("Thinking..."):
                    response = st.session_state.agent.chat(quick_q)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": response}
                )
                st.rerun()

        # ── Chat Input ────────────────────────────────────
        user_input = st.chat_input(
            "Ask about your cloud resources... "
            "e.g. 'Why can't I SSH into my EC2?'"
        )

        if user_input:
            st.session_state.chat_messages.append(
                {"role": "user", "content": user_input}
            )
            with st.spinner("☁️ Agent is thinking..."):
                response = st.session_state.agent.chat(user_input)
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": response}
            )
            st.rerun()

    # ══════════════════════════════════════════════════════════
    # TAB 4 — Export Report
    # ══════════════════════════════════════════════════════════
    with tab4:
        st.markdown("## 📥 Export Scan Report")

        text_report = generate_text_report(results)

        st.text_area(
            "Plain Text Report (copy or download)",
            value=text_report,
            height=400
        )

        dl_col1, dl_col2 = st.columns(2)

        with dl_col1:
            st.download_button(
                label="⬇️ Download Report (.txt)",
                data=text_report,
                file_name=f"cloudops_report_{meta['region']}.txt",
                mime="text/plain",
                use_container_width=True
            )

        with dl_col2:
            json_report = json.dumps(results, indent=2, default=str)
            st.download_button(
                label="⬇️ Download Raw Data (.json)",
                data=json_report,
                file_name=f"cloudops_data_{meta['region']}.json",
                mime="application/json",
                use_container_width=True
            )

        # ── AI Analysis in Report ─────────────────────────
        st.markdown("### 🤖 AI Analysis (for report)")
        if st.session_state.ai_analysis:
            st.text_area(
                "AI Analysis Text",
                value=st.session_state.ai_analysis,
                height=300
            )
            st.download_button(
                label="⬇️ Download AI Analysis (.txt)",
                data=st.session_state.ai_analysis,
                file_name=f"cloudops_ai_analysis_{meta['region']}.txt",
                mime="text/plain"
            )

# ─── LANDING PAGE (before scan) ───────────────────────────────
else:
    if not scan_button:
        st.markdown("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            ### 🔍 Intelligent Scanning
            Automatically scans all your AWS resources for
            misconfigurations, connectivity issues, and
            security vulnerabilities.
            """)

        with col2:
            st.markdown("""
            ### 🤖 AI-Powered Analysis
            Amazon Bedrock Nova analyzes every finding,
            explains what's wrong, why it matters,
            and gives exact fix steps.
            """)

        with col3:
            st.markdown("""
            ### 💬 Interactive Chat
            Chat with the AI agent about your specific
            resources. Ask follow-up questions and get
            personalized guidance.
            """)

        st.markdown("---")

        st.info(
            "👈 **Click 'Start Full AWS Scan' in the sidebar to begin!** "
            "Make sure your EC2 IAM Role has ReadOnly + Bedrock access."
        )

        # ── Feature Preview ───────────────────────────────
        st.markdown("### 🎯 What gets checked:")

        prev_col1, prev_col2, prev_col3 = st.columns(3)

        with prev_col1:
            st.markdown("""
            **🖥️ EC2**
            - Public IP assigned?
            - SSH port 22 open?
            - Key pair attached?
            - Instance state

            **🗄️ RDS**
            - Port accessible?
            - Backups enabled?
            - Encryption on?
            - Multi-AZ setup?
            """)

        with prev_col2:
            st.markdown("""
            **🪣 S3**
            - Public access blocked?
            - Versioning enabled?
            - Encryption enabled?
            - Logging enabled?

            **⚡ Lambda**
            - Timeout configured?
            - Deprecated runtime?
            - VPC connectivity?
            - Memory sufficient?
            """)

        with prev_col3:
            st.markdown("""
            **🔒 Security Groups**
            - Ports open to world?
            - Dangerous ports exposed?
            - Unrestricted access?

            **👤 IAM**
            - Root MFA enabled?
            - Old access keys?
            - Users without MFA?
            """)