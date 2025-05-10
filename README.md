# AWS Landing Zone CLI

A command-line tool for automating the setup and management of AWS Landing Zones using AWS Organizations and CloudFormation. This tool helps create and manage a multi-account AWS environment with security, networking, and shared services.

## Features

- Create and manage AWS Organizations structure
- Automated account creation and configuration
- Deployment of security, networking, and shared services
- Centralized logging and security monitoring
- Infrastructure as Code using CloudFormation

## Prerequisites

1. **AWS Credentials**
   - AWS Organizations admin access in management account
   - Credentials configured in `~/.aws/credentials` or environment variables
   - Permissions to create accounts, OUs, and deploy CloudFormation

2. **Python Environment**
   - Python 3.7 or higher
   - Required packages: boto3, PyYAML, typer, rich

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd aws-landing-zone-cli
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure AWS credentials:
   ```bash
   aws configure
   ```

## Configuration

Edit `configs/accounts.yaml` to define your organizational structure:

```yaml
organizational_units:
  Security:
    parent_id: "r-xxxx"  # Your org root ID
    accounts:
      - name: security-tools
        email: security@yourdomain.com
```

## Available Commands

### 1. Complete Landing Zone Setup
```bash
python org_cli.py launch --env prod --region us-east-1
```
This command:
- Creates all OUs defined in accounts.yaml
- Creates accounts under each OU
- Deploys templates in this order:
  1. Logging account: CloudTrail, central S3 bucket
  2. Security account: GuardDuty, SecurityHub, Config
  3. Infrastructure accounts: VPC, shared services

### 2. Individual Account Management

Create an OU:
```bash
python org_cli.py create-ou --name "Security" --parent-id "r-xxxx"
```
- Creates a new Organizational Unit
- parent-id can be root ID or another OU ID

Create an account:
```bash
python org_cli.py create-account --name "security-tools" --email "security@domain.com" --ou "ou-xxxx"
```
- Creates a new AWS account
- Optionally moves it to specified OU
- Email must be unique across all AWS accounts

### 3. Stack Management

Deploy a stack:
```bash
python org_cli.py deploy-stack --account-id "123456789012" --template "security.yaml"
```
- Assumes OrganizationAccountAccessRole in target account
- Deploys or updates specified CloudFormation template
- Waits for stack operation to complete

Delete a stack:
```bash
python org_cli.py delete-stack --account-id "123456789012" --stack-name "landing-zone-vpc-base"
```
- Removes CloudFormation stack and all its resources
- Waits for deletion to complete

### 4. Organization Management

List accounts:
```bash
python org_cli.py list-accounts
```
- Shows all accounts in the organization
- Displays account names and IDs in a table format

Delete account:
```bash
python org_cli.py delete-account --account-id "123456789012"
```
- Moves account to root
- Initiates account closure
- Note: Takes up to 90 days to complete

Delete OU:
```bash
python org_cli.py delete-ou --ou-id "ou-xxxx"
```
- Deletes an empty Organizational Unit
- Fails if OU contains accounts

### 5. Cleanup

Remove everything:
```bash
python org_cli.py cleanup --env prod
```
- Deletes resources in reverse order
- Removes stacks from each account
- Closes accounts
- Deletes OUs
- Use with caution!

## CloudFormation Templates

1. **vpc-base.yaml**
   - Complete VPC setup
   - Public and private subnets
   - NAT Gateways
   - Route tables

2. **security.yaml**
   - GuardDuty threat detection
   - SecurityHub setup
   - AWS Config recorder

3. **logging.yaml**
   - Central logging bucket
   - CloudTrail configuration
   - Log retention policies

4. **shared-services.yaml**
   - Shared S3 buckets
   - ECR repositories
   - KMS encryption keys

5. **org-setup.yaml**
   - Service Control Policies
   - Root account restrictions

## Error Handling

- All commands include error checking
- Clear error messages displayed
- Progress indicators for long operations
- Automatic retry for some AWS operations

## Best Practices

1. Always test in a development environment first
2. Use unique email addresses for each account
3. Keep track of account IDs and OU IDs
4. Review CloudFormation templates before deployment
5. Monitor AWS CloudTrail for all operations

## Troubleshooting

Common issues:
1. Insufficient permissions
2. Email address already in use
3. Account limit reached
4. Stack deployment failures

For errors:
- Check AWS Organizations console
- Review CloudWatch Logs
- Verify AWS credentials
- Ensure proper role assumptions

## Security Considerations

1. Root account access is denied by default
2. All S3 buckets block public access
3. CloudTrail enabled in all accounts
4. GuardDuty monitors for threats
5. AWS Config tracks resource changes

## Support

For issues and feature requests:
- Open a GitHub issue
- Include error messages and logs
- Specify AWS region and account type
