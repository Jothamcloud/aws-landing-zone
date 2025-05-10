import boto3
import time
from botocore.exceptions import ClientError, WaiterError
from typing import Optional, Dict, List
from .logger import setup_logging

logger = setup_logging()

class OrganizationHelper:
    """Helper class to manage AWS Organizations operations"""
    
    def __init__(self, region: str):
        """Initialize with region"""
        self.org_client = boto3.client('organizations', region_name=region)
        self.sts = boto3.client('sts', region_name=region)
        
    def create_organizational_unit(self, name: str, parent_id: str) -> dict:
        """
        Create an organizational unit
        
        Args:
            name: Name of the OU
            parent_id: ID of parent OU or root
            
        Returns:
            dict: Created OU details
        """
        try:
            response = self.org_client.create_organizational_unit(
                ParentId=parent_id,
                Name=name
            )
            return response['OrganizationalUnit']
        except ClientError as e:
            raise e

    def create_account(self, name: str, email: str, ou_id: Optional[str] = None) -> dict:
        """
        Create a new AWS account and wait for completion
        
        Args:
            name: Account name
            email: Root email for account
            ou_id: Optional OU to place account in
            
        Returns:
            dict: Created account details
        """
        try:
            logger.info(f"Creating account: {name}")
            response = self.org_client.create_account(
                AccountName=name,
                Email=email
            )
            
            request_id = response['CreateAccountStatus']['Id']
            
            # Wait for account creation to complete
            status = self._wait_for_account_creation(request_id)
            
            if status['State'] == 'SUCCEEDED':
                account_id = status['AccountId']
                logger.info(f"Account created successfully: {account_id}")
                
                if ou_id:
                    logger.info(f"Moving account to OU: {ou_id}")
                    self.org_client.move_account(
                        AccountId=account_id,
                        SourceParentId=self._get_root_id(),
                        DestinationParentId=ou_id
                    )
                    
                return status
            else:
                error_messages = {
                    'EMAIL_ALREADY_EXISTS': 'Email address is already in use',
                    'ACCOUNT_LIMIT_EXCEEDED': 'Account limit has been exceeded',
                    'INVALID_EMAIL': 'Invalid email address provided',
                    'INVALID_ADDRESS': 'Invalid address provided',
                    'CONCURRENT_ACCOUNT_MODIFICATION': 'Another account operation in progress'
                }
                error_msg = error_messages.get(status['FailureReason'], status['FailureReason'])
                raise Exception(error_msg)
                
        except ClientError as e:
            logger.error(f"Failed to create account: {str(e)}")
            raise
            
    def _wait_for_account_creation(self, request_id: str, max_retries: int = 20) -> dict:
        """Wait for account creation to complete"""
        for _ in range(max_retries):
            status = self.org_client.describe_create_account_status(
                CreateAccountRequestId=request_id
            )['CreateAccountStatus']
            
            if status['State'] in ['SUCCEEDED', 'FAILED']:
                return status
                
            logger.info(f"Waiting for account creation... Current state: {status['State']}")
            time.sleep(30)
            
        raise TimeoutError("Account creation timed out")

    def attach_policy(self, policy_id: str, target_id: str) -> dict:
        """
        Attach an SCP to an OU or account
        
        Args:
            policy_id: ID of the service control policy
            target_id: ID of the target OU or account
            
        Returns:
            dict: Response from attach operation
        """
        try:
            response = self.org_client.attach_policy(
                PolicyId=policy_id,
                TargetId=target_id
            )
            return response
        except ClientError as e:
            raise e

    def list_accounts(self) -> List[Dict]:
        """
        List all accounts in organization
        
        Returns:
            List[Dict]: List of account details
        """
        try:
            response = self.org_client.list_accounts()
            return response['Accounts']
        except ClientError as e:
            raise e

    def _get_root_id(self) -> str:
        """Get the organization root ID"""
        try:
            response = self.org_client.list_roots()
            return response['Roots'][0]['Id']
        except ClientError as e:
            raise e

    def delete_account(self, account_id: str) -> dict:
        """Delete an AWS account"""
        try:
            # First move account to root
            root_id = self._get_root_id()
            current_parent = self.org_client.list_parents(ChildId=account_id)['Parents'][0]['Id']
            
            if current_parent != root_id:
                self.org_client.move_account(
                    AccountId=account_id,
                    SourceParentId=current_parent,
                    DestinationParentId=root_id
                )
            
            # Then close account
            response = self.org_client.close_account(AccountId=account_id)
            return response
        except ClientError as e:
            logger.error(f"Failed to delete account: {str(e)}")
            raise

    def delete_organizational_unit(self, ou_id: str) -> dict:
        """Delete an organizational unit"""
        try:
            response = self.org_client.delete_organizational_unit(
                OrganizationalUnitId=ou_id
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to delete OU: {str(e)}")
            raise

    def get_account_id_by_name(self, account_name: str) -> Optional[str]:
        """Get account ID by name"""
        try:
            accounts = self.list_accounts()
            for account in accounts:
                if account['Name'] == account_name:
                    return account['Id']
            return None
        except ClientError as e:
            logger.error(f"Failed to get account ID: {str(e)}")
            raise

    def get_ou_id_by_name(self, ou_name: str) -> Optional[str]:
        """Get OU ID by name"""
        try:
            root_id = self._get_root_id()
            response = self.org_client.list_organizational_units_for_parent(
                ParentId=root_id
            )
            for ou in response['OrganizationalUnits']:
                if ou['Name'] == ou_name:
                    return ou['Id']
            return None
        except ClientError as e:
            logger.error(f"Failed to get OU ID: {str(e)}")
            raise
