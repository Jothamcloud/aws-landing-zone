import typer
import yaml
from pathlib import Path
from typing import Optional
from utils.cloudformation import CloudFormationHelper
from utils.org_helper import OrganizationHelper

app = typer.Typer()

@app.command()
def launch(
    env: str = typer.Option(..., help="Environment name (dev/prod)"),
    region: str = typer.Option("us-east-1", help="AWS region")
):
    """Launch complete landing zone setup"""
    # Load configuration
    with open("configs/accounts.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    org_helper = OrganizationHelper(region)
    
    # Create OUs and accounts
    for ou_name, ou_config in config["organizational_units"].items():
        ou = org_helper.create_organizational_unit(ou_name, ou_config["parent_id"])
        
        for account in ou_config.get("accounts", []):
            org_helper.create_account(
                name=account["name"],
                email=account["email"],
                ou_id=ou["Id"]
            )

@app.command()
def create_ou(
    name: str = typer.Option(..., help="Name of the organizational unit"),
    parent_id: str = typer.Option(..., help="Parent OU or root ID")
):
    """Create an organizational unit"""
    org_helper = OrganizationHelper("us-east-1")
    result = org_helper.create_organizational_unit(name, parent_id)
    typer.echo(f"Created OU: {result}")

@app.command()
def create_account(
    name: str = typer.Option(..., help="Account name"),
    email: str = typer.Option(..., help="Root email for account"),
    ou: Optional[str] = typer.Option(None, help="OU ID to place account in")
):
    """Create an AWS account"""
    org_helper = OrganizationHelper("us-east-1")
    result = org_helper.create_account(name, email, ou)
    typer.echo(f"Created account: {result}")

@app.command()
def deploy_stack(
    account_id: str = typer.Option(..., help="AWS account ID"),
    template: str = typer.Option(..., help="Template file name"),
    region: str = typer.Option("us-east-1", help="AWS region")
):
    """Deploy a CloudFormation stack to an account"""
    role_arn = f"arn:aws:iam::{account_id}:role/OrganizationAccountAccessRole"
    
    # Load template
    template_path = Path("templates") / template
    with open(template_path, "r") as f:
        template_body = f.read()
    
    cfn = CloudFormationHelper(region, role_arn)
    result = cfn.deploy_stack(
        stack_name=f"landing-zone-{template.replace('.yaml', '')}",
        template_body=template_body
    )
    typer.echo(f"Stack deployment result: {result}")

@app.command()
def attach_scp(
    policy_id: str = typer.Option(..., help="Service Control Policy ID"),
    target_id: str = typer.Option(..., help="Target OU or account ID")
):
    """Attach a Service Control Policy"""
    org_helper = OrganizationHelper("us-east-1")
    result = org_helper.attach_policy(policy_id, target_id)
    typer.echo(f"Policy attachment result: {result}")

@app.command()
def list_accounts():
    """List all accounts in the organization"""
    org_helper = OrganizationHelper("us-east-1")
    accounts = org_helper.list_accounts()
    for account in accounts:
        typer.echo(f"Account: {account['Name']} ({account['Id']})")

if __name__ == "__main__":
    app()
