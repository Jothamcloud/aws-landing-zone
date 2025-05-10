import typer
import yaml
from pathlib import Path
from typing import Optional
from utils.cloudformation import CloudFormationHelper
from utils.org_helper import OrganizationHelper
from utils.logger import setup_logging, console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer()
logger = setup_logging()

@app.command()
def launch(
    env: str = typer.Option(..., help="Environment name (dev/prod)"),
    region: str = typer.Option("us-east-1", help="AWS region")
):
    """Launch complete landing zone setup"""
    try:
        # Load and validate configuration
        logger.info("Loading configuration...")
        with open("configs/accounts.yaml", "r") as f:
            config = yaml.safe_load(f)

        if not config.get("organizational_units"):
            raise ValueError("No organizational units defined in config")

        org_helper = OrganizationHelper(region)
        cfn_helper = CloudFormationHelper(region)
        
        # Deployment order: Logging -> Security -> Infrastructure
        deployment_order = ["Logging", "Security", "Infrastructure"]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Create OUs and accounts in order
            for ou_type in deployment_order:
                if ou_type not in config["organizational_units"]:
                    continue
                    
                ou_config = config["organizational_units"][ou_type]
                task_id = progress.add_task(f"Setting up {ou_type}...", total=None)
                
                try:
                    # Create OU
                    ou = org_helper.create_organizational_unit(ou_type, ou_config["parent_id"])
                    logger.info(f"Created OU: {ou_type}")
                    
                    # Create accounts
                    for account in ou_config.get("accounts", []):
                        status = org_helper.create_account(
                            name=account["name"],
                            email=account["email"],
                            ou_id=ou["Id"]
                        )
                        
                        # Deploy appropriate template based on account type
                        if status['State'] == 'SUCCEEDED':
                            account_id = status['AccountId']
                            template_map = {
                                "Logging": "logging.yaml",
                                "Security": "security.yaml",
                                "Infrastructure": ["vpc-base.yaml", "shared-services.yaml"]
                            }
                            
                            templates = template_map.get(ou_type, [])
                            if isinstance(templates, str):
                                templates = [templates]
                                
                            for template in templates:
                                logger.info(f"Deploying {template} to account {account_id}")
                                template_path = Path("templates") / template
                                with open(template_path, "r") as f:
                                    template_body = f.read()
                                    
                                cfn_helper.deploy_stack(
                                    stack_name=f"landing-zone-{template.replace('.yaml', '')}",
                                    template_body=template_body
                                )
                    
                    progress.update(task_id, completed=True)
                except Exception as e:
                    logger.error(f"Failed to set up {ou_type}: {str(e)}")
                    progress.update(task_id, completed=True, description=f"Failed to set up {ou_type}")
                    raise
                
            logger.info("Landing zone deployment completed successfully!")
            
    except Exception as e:
        logger.error(f"Landing zone deployment failed: {str(e)}")
        raise typer.Exit(1)

@app.command()
def create_ou(
    name: str = typer.Option(..., help="Name of the organizational unit"),
    parent_id: str = typer.Option(..., help="Parent OU or root ID")
):
    """Create an organizational unit"""
    try:
        org_helper = OrganizationHelper("us-east-1")
        result = org_helper.create_organizational_unit(name, parent_id)
        console.print(f"\n[green]Successfully created OU:[/green]")
        console.print(f"  Name: {result['Name']}")
        console.print(f"  ID: {result['Id']}")
        console.print(f"  ARN: {result['Arn']}\n")
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {str(e)}\n")
        raise typer.Exit(1)

@app.command()
def create_account(
    name: str = typer.Option(..., help="Account name"),
    email: str = typer.Option(..., help="Root email for account"),
    ou: Optional[str] = typer.Option(None, help="OU ID to place account in")
):
    """Create an AWS account"""
    try:
        org_helper = OrganizationHelper("us-east-1")
        result = org_helper.create_account(name, email, ou)
        console.print(f"\n[green]Successfully created account:[/green]")
        console.print(f"  Name: {result['AccountName']}")
        console.print(f"  ID: {result['AccountId']}\n")
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {str(e)}\n")
        raise typer.Exit(1)

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
    try:
        org_helper = OrganizationHelper("us-east-1")
        accounts = org_helper.list_accounts()
        
        # Print header
        console.print("\n[bold]AWS Organization Accounts[/bold]\n")
        
        # Print accounts in a table format
        from rich.table import Table
        table = Table(show_header=True)
        table.add_column("Account Name", style="cyan")
        table.add_column("Account ID", style="green")
        
        for account in accounts:
            table.add_row(account['Name'], account['Id'])
        
        console.print(table)
        console.print()
    except Exception as e:
        if "Unable to locate credentials" in str(e):
            console.print("\n[red]Error:[/red] AWS credentials not found. Please configure your AWS credentials.")
            console.print("Run: [bold]aws configure[/bold]\n")
        else:
            console.print(f"\n[red]Error:[/red] {str(e)}\n")
        raise typer.Exit(1)

@app.command()
def delete_stack(
    account_id: str = typer.Option(..., help="AWS account ID"),
    stack_name: str = typer.Option(..., help="Stack name to delete"),
    region: str = typer.Option("us-east-1", help="AWS region")
):
    """Delete a CloudFormation stack from an account"""
    try:
        role_arn = f"arn:aws:iam::{account_id}:role/OrganizationAccountAccessRole"
        cfn = CloudFormationHelper(region, role_arn)
        result = cfn.delete_stack(stack_name)
        typer.echo(f"Stack deletion initiated: {result}")
    except Exception as e:
        logger.error(f"Failed to delete stack: {str(e)}")
        raise typer.Exit(1)

@app.command()
def delete_account(
    account_id: str = typer.Option(..., help="AWS account ID"),
    region: str = typer.Option("us-east-1", help="AWS region")
):
    """Remove account from OU and close it"""
    try:
        org_helper = OrganizationHelper(region)
        result = org_helper.delete_account(account_id)
        console.print(f"\n[yellow]Account deletion initiated[/yellow]")
        console.print(f"Account ID: {account_id}")
        console.print("[yellow]Note: Account deletion process may take up to 90 days to complete[/yellow]\n")
    except Exception as e:
        logger.error(f"Failed to delete account: {str(e)}")
        raise typer.Exit(1)

@app.command()
def delete_ou(
    ou_id: str = typer.Option(..., help="OU ID to delete"),
    region: str = typer.Option("us-east-1", help="AWS region")
):
    """Delete an organizational unit (must be empty)"""
    try:
        org_helper = OrganizationHelper(region)
        result = org_helper.delete_organizational_unit(ou_id)
        console.print(f"\n[green]Successfully deleted OU:[/green] {ou_id}\n")
    except Exception as e:
        logger.error(f"Failed to delete OU: {str(e)}")
        raise typer.Exit(1)

@app.command()
def cleanup(
    env: str = typer.Option(..., help="Environment name (dev/prod)"),
    region: str = typer.Option("us-east-1", help="AWS region")
):
    """Cleanup all resources in reverse order"""
    try:
        # Load configuration
        with open("configs/accounts.yaml", "r") as f:
            config = yaml.safe_load(f)

        org_helper = OrganizationHelper(region)
        
        # Reverse deployment order
        deployment_order = ["Infrastructure", "Security", "Logging"]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for ou_type in deployment_order:
                if ou_type not in config["organizational_units"]:
                    continue
                    
                task_id = progress.add_task(f"Cleaning up {ou_type}...", total=None)
                try:
                    ou_config = config["organizational_units"][ou_type]
                    
                    # Delete accounts in OU
                    for account in ou_config.get("accounts", []):
                        logger.info(f"Cleaning up account: {account['name']}")
                        # First delete stacks
                        template_map = {
                            "Logging": ["logging.yaml"],
                            "Security": ["security.yaml"],
                            "Infrastructure": ["vpc-base.yaml", "shared-services.yaml"]
                        }
                        
                        # Get account ID
                        account_id = org_helper.get_account_id_by_name(account["name"])
                        if account_id:
                            cfn = CloudFormationHelper(region, f"arn:aws:iam::{account_id}:role/OrganizationAccountAccessRole")
                            for template in template_map.get(ou_type, []):
                                stack_name = f"landing-zone-{template.replace('.yaml', '')}"
                                cfn.delete_stack(stack_name)
                            
                            # Then delete account
                            org_helper.delete_account(account_id)
                    
                    # Delete OU
                    ou_id = org_helper.get_ou_id_by_name(ou_type)
                    if ou_id:
                        org_helper.delete_organizational_unit(ou_id)
                        
                    progress.update(task_id, completed=True)
                except Exception as e:
                    logger.error(f"Failed to clean up {ou_type}: {str(e)}")
                    progress.update(task_id, completed=True, description=f"Failed to clean up {ou_type}")
                    raise
                
        logger.info("Cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
