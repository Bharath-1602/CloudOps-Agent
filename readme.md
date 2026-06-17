This is a CloudOps Agent


Steps :
1. Launch EC2 Instance:
 Attach IAM Role with these policies:
  - ReadOnlyAccess (for scanning)
  - AmazonBedrockFullAccess (for Nova)

2. Create IAM Role for EC2:
IAM Console → Roles → Create Role
→ EC2 use case
→ Attach policies:
   ✅ ReadOnlyAccess
   ✅ AmazonBedrockFullAccess
→ Name it: CloudOpsAgentRole
→ Attach role to your EC2 instance

3. Security Group for EC2:
Inbound Rules:
  - SSH (22)   → Your IP
  - Custom TCP (8501) → Your IP  ← Streamlit port

4. Install and run:

SSH into ur EC2 instance :

sudo apt update && sudo apt install python3 python3-pip git -y

git clone https://github.com/Bharath-1602/CloudOps-Agent.git

cd CloudOps-Agent

sudo apt install -y python3-venv

python3 -m venv venv

source venv/bin/activate

pip install --upgrade pip

pip install -r requirements.txt

streamlit run app.py --server.port 8501 --server.address 0.0.0.0

