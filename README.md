# AWS Landing Zone CLI

A command-line tool for automating the setup and management of AWS Landing Zones using AWS Organizations and CloudFormation.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

The CLI provides several commands for managing your AWS Landing Zone:

### Launch Complete Landing Zone

```bash
python org_cli.py launch --env prod --region us-east-1
```

### Create Organizational Unit

```bash
python org_cli.py create-ou --name "Security" --parent-id "r-xxxx"
```

### Create AWS Account

```bash
python org_cli.py create-account --name "security-tools" --email "security@yourdomain.com" --ou "ou-xxxx"
```

### Deploy CloudFormation Stack

```bash
python org_cli.py deploy-stack --account-id "123456789012" --template "security.yaml"
```

### Attach Service Control Policy

```bash
python org_cli.py attach-scp --policy-id "p-xxxx" --target-id "ou-xxxx"
```

### List Accounts

```bash
python org_cli.py list-accounts
```

## Configuration

Edit `configs/accounts.yaml` to define your organizational structure and account details.

## Templates

CloudFormation templates in the `templates/` directory:
- org-setup.yaml: Service Control Policies
- vpc-base.yaml: VPC and networking
- security.yaml: Security tools
- logging.yaml: Logging configuration
- shared-services.yaml: Shared infrastructure

## Prerequisites

- AWS credentials configured with appropriate permissions
- Python 3.7+
- Required Python packages (see requirements.txt)
